// Fix for "Cannot read properties of null (reading 'value')" error
(function() {
  // Run on page load
  document.addEventListener('DOMContentLoaded', function() {
    console.log("FiLot wallet value protection script loaded");
    
    // First, initialize a default global value to use when needed
    window.DEFAULT_WALLET_VALUE = {
      address: null,
      balance: 0,
      status: "pending"
    };
    
    // Check if any elements with data-connection exist and fix them
    function fixExistingConnectionElements() {
      const elements = document.querySelectorAll('[data-connection]');
      elements.forEach(function(element) {
        try {
          const data = JSON.parse(element.getAttribute('data-connection') || '{}');
          if (data && !data.value) {
            data.value = window.DEFAULT_WALLET_VALUE;
            element.setAttribute('data-connection', JSON.stringify(data));
          }
        } catch (e) {
          console.warn("Error fixing connection data:", e);
        }
      });
    }
    
    // Run the fix immediately and periodically
    fixExistingConnectionElements();
    setInterval(fixExistingConnectionElements, 1000);
    
    // Patch global window object to ensure connection_data always has a value property
    const originalSetConnectionData = window.setConnectionData;
    if (typeof originalSetConnectionData === 'function') {
      window.setConnectionData = function(data) {
        // Make sure data exists
        if (!data) {
          data = {};
        }
        
        // Make sure connection_data exists
        if (!data.connection_data) {
          data.connection_data = {};
        }
        
        // Make sure value exists in connection_data
        if (!data.connection_data.value) {
          data.connection_data.value = window.DEFAULT_WALLET_VALUE;
        }
        
        // Call the original function with our protected data
        return originalSetConnectionData(data);
      };
      console.log("Patched setConnectionData to prevent null value errors");
    }
    
    // Add a global protection for any access to .value properties
    window.safeGetValue = function(obj) {
      if (!obj) return { address: null, balance: 0, status: "pending" };
      if (!obj.value) return { address: null, balance: 0, status: "pending" };
      return obj.value;
    };
    
    // Monitor all button clicks to add additional safety
    document.addEventListener('click', function(event) {
      // Protect against null errors in callbacks
      setTimeout(function() {
        // For any elements that might have connection_data without value
        const elements = document.querySelectorAll('[data-connection]');
        elements.forEach(function(element) {
          try {
            const data = JSON.parse(element.getAttribute('data-connection'));
            if (data && !data.value) {
              data.value = { address: null, balance: 0, status: "pending" };
              element.setAttribute('data-connection', JSON.stringify(data));
            }
          } catch (e) {
            console.log("Error protecting connection data:", e);
          }
        });
      }, 100);
    });
  });
})();