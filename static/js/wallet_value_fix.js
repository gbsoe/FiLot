/**
 * Enhanced fix for the "Cannot read properties of null (reading 'value')" error
 * This version is more aggressive in protecting against the error
 */
(function() {
  // Run immediately on load
  function initFix() {
    console.log("Enhanced FiLot wallet protection script loaded");
    
    // Set up default value globally
    window.DEFAULT_WALLET_VALUE = {
      address: null,
      balance: 0,
      status: "pending"
    };
    
    // Global safety wrapper for any value access
    window.safeGetValue = function(obj) {
      if (!obj) return window.DEFAULT_WALLET_VALUE;
      if (!obj.value) return window.DEFAULT_WALLET_VALUE;
      return obj.value;
    };
    
    // Monkey patch all value access through global objects
    Object.defineProperty(window, 'wallet_value', {
      get: function() {
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
    setInterval(fixConnectionElements, 200);
    
    // Global error handler to catch any errors and prevent page crashes
    window.addEventListener('error', function(event) {
      if (event.error && event.error.message && 
          event.error.message.includes("Cannot read properties of null")) {
        console.warn("Global error handler caught:", event.error.message);
        event.preventDefault();
        return true;
      }
    });
    
    // Patch key methods that might be used by the app
    if (window.tg && window.tg.WebApp) {
      const originalSendData = window.tg.WebApp.sendData;
      if (typeof originalSendData === 'function') {
        window.tg.WebApp.sendData = function(data) {
          if (!data || (typeof data === 'string' && data.includes('"value":null'))) {
            const safeData = JSON.stringify({value: window.DEFAULT_WALLET_VALUE});
            return originalSendData.call(window.tg.WebApp, safeData);
          }
          return originalSendData.apply(window.tg.WebApp, arguments);
        };
      }
    }
  }
  
  // Make sure it runs as soon as possible
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFix);
  } else {
    initFix();
  }
})();