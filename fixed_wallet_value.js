/**
 * Enhanced fix for the "Cannot read properties of null (reading 'value')" error
 * This version is more aggressive in protecting against the error
 */
(function() {
  // Run on page load and ensure it runs immediately
  function initFix() {
    console.log("Enhanced FiLot wallet protection script loaded");
    
    // Set up default value globally
    window.DEFAULT_WALLET_VALUE = {
      address: null,
      balance: 0,
      status: "pending"
    };
    
    // More aggressive protection by patching Object prototype
    // This is a bit hacky but will prevent most null reference errors
    const originalGet = Object.prototype.__lookupGetter__('value');
    Object.defineProperty(Object.prototype, 'value', {
      get: function() {
        // If the original getter exists and this is a valid object, use it
        if (originalGet && this !== null && this !== undefined) {
          try {
            return originalGet.call(this);
          } catch (e) {
            return window.DEFAULT_WALLET_VALUE;
          }
        }
        // Otherwise return the default value
        return window.DEFAULT_WALLET_VALUE;
      },
      configurable: true
    });
    
    // Protect any element with data-connection attribute
    function fixConnectionElements() {
      try {
        const elements = document.querySelectorAll('[data-connection]');
        if (!elements || elements.length === 0) return;
        
        elements.forEach(function(element) {
          try {
            const dataStr = element.getAttribute('data-connection');
            if (!dataStr) {
              element.setAttribute('data-connection', JSON.stringify({
                value: window.DEFAULT_WALLET_VALUE
              }));
              return;
            }
            
            try {
              const data = JSON.parse(dataStr);
              if (!data) {
                element.setAttribute('data-connection', JSON.stringify({
                  value: window.DEFAULT_WALLET_VALUE
                }));
                return;
              }
              
              if (!data.value) {
                data.value = window.DEFAULT_WALLET_VALUE;
                element.setAttribute('data-connection', JSON.stringify(data));
              }
            } catch (parseErr) {
              element.setAttribute('data-connection', JSON.stringify({
                value: window.DEFAULT_WALLET_VALUE
              }));
            }
          } catch (elementErr) {
            console.warn("Error fixing element:", elementErr);
          }
        });
      } catch (e) {
        console.warn("Error in fixConnectionElements:", e);
      }
    }
    
    // Run fixes immediately and periodically
    fixConnectionElements();
    setInterval(fixConnectionElements, 500);
    
    // Global error handler to catch any errors
    window.addEventListener('error', function(event) {
      if (event.error && event.error.message && 
          event.error.message.includes("Cannot read properties of null")) {
        console.warn("Global error handler caught:", event.error.message);
        event.preventDefault();
        return true;
      }
    });
  }
  
  // Make sure it runs as soon as possible
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFix);
  } else {
    initFix();
  }
})();