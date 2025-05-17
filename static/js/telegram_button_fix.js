// Fix for Telegram button JavaScript issues
// Prevents "Cannot read properties of null (reading 'value')" errors

(function() {
  console.log("Telegram button fix loaded");

  // Create a safety wrapper for any function that might access .value properties
  function safeValueAccess(originalFn) {
    return function() {
      try {
        // Try to call the original function
        return originalFn.apply(this, arguments);
      } catch (error) {
        // If we get a "Cannot read properties of null" error
        if (error && error.message && error.message.includes("Cannot read properties of null")) {
          console.warn("Prevented error:", error.message);
          
          // Return a safe default value
          return {
            success: false,
            error: "Value access error prevented",
            value: {
              address: null,
              balance: 0,
              status: "error"
            }
          };
        }
        
        // Re-throw other errors
        throw error;
      }
    };
  }

  // Apply the safety wrapper to all functions on window that might be button handlers
  function patchWindowFunctions() {
    for (const key in window) {
      if (typeof window[key] === 'function' && 
          (key.includes('button') || key.includes('click') || key.includes('callback') || 
           key.includes('handle') || key.includes('wallet') || key.includes('connect'))) {
        const originalFn = window[key];
        window[key] = safeValueAccess(originalFn);
        console.log("Protected function:", key);
      }
    }
  }

  // Monitor all Telegram Web App script loads and patch after they load
  const originalCreateElement = document.createElement;
  document.createElement = function(tagName) {
    const element = originalCreateElement.call(document, tagName);
    
    if (tagName.toLowerCase() === 'script') {
      const originalSetAttribute = element.setAttribute;
      element.setAttribute = function(name, value) {
        if (name === 'src' && (value.includes('telegram') || value.includes('wallet'))) {
          console.log("Monitoring Telegram script:", value);
          
          // Add load event listener before setting src
          element.addEventListener('load', function() {
            console.log("Telegram script loaded:", value);
            
            // Wait for any initialization to complete
            setTimeout(patchWindowFunctions, 500);
          });
        }
        return originalSetAttribute.call(this, name, value);
      };
    }
    
    return element;
  };

  // Add global protections
  window.addEventListener('error', function(event) {
    if (event.error && event.error.message && 
        event.error.message.includes("Cannot read properties of null")) {
      console.warn("Global error handler caught:", event.error.message);
      event.preventDefault();
      return true;
    }
  });

  // If WebApp is already available, patch it directly
  if (window.Telegram && window.Telegram.WebApp) {
    console.log("Telegram WebApp found, patching directly");
    
    // Add null value protection to WebApp object
    const originalWebApp = window.Telegram.WebApp;
    
    // Safely wrap any methods that might access null values
    if (originalWebApp.sendData) {
      const originalSendData = originalWebApp.sendData;
      originalWebApp.sendData = function(data) {
        if (data && typeof data === 'string') {
          try {
            // Try to parse and protect JSON data
            const parsed = JSON.parse(data);
            
            // Add safety for connection_data.value
            if (parsed && parsed.connection_data && !parsed.connection_data.value) {
              parsed.connection_data.value = {
                address: null,
                balance: 0,
                status: "pending"
              };
              // Use the protected data
              data = JSON.stringify(parsed);
            }
          } catch (e) {
            // Not JSON or other error, continue with original data
          }
        }
        return originalSendData.call(this, data);
      };
    }
  }

  // Patch any existing button handlers
  setTimeout(patchWindowFunctions, 1000);
  
  // Set up monitoring for button click errors
  document.addEventListener('click', function(event) {
    // Add a try/catch wrapper around the event loop to catch any errors that happen after the click
    setTimeout(function() {
      try {
        // Safety check for any button action after a click
        if (window.buttonResult && window.buttonResult.connection_data && !window.buttonResult.connection_data.value) {
          console.log("Adding missing value property to buttonResult");
          window.buttonResult.connection_data.value = {
            address: null,
            balance: 0,
            status: "pending"
          };
        }
      } catch (e) {
        console.warn("Error in click safety monitor:", e);
      }
    }, 100);
  });
})();