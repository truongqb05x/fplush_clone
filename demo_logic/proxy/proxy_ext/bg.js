(function() {
  'use strict';
  
  console.log("[Proxy Extension] Background script starting...");
  
  var PROXY_HOST = "proxy-s1.resident-psun.io.vn";
  var PROXY_PORT = 20028;
  var PROXY_USER = "sun5020028";
  var PROXY_PASS = "JbW9MMqxO63U";
  
  // Note: Proxy is set via --proxy-server argument
  // This extension only handles authentication
  console.log("[Proxy Extension] Proxy server set via command line:", PROXY_HOST + ":" + PROXY_PORT);
  console.log("[Proxy Extension] Extension will handle authentication only");
  
  // Handle authentication - try multiple approaches
  function handleAuth(details, callback) {
    console.log("[Proxy Extension] 🔐 Auth required!");
    console.log("[Proxy Extension] URL:", details.url);
    console.log("[Proxy Extension] Challenger:", details.challenger);
    console.log("[Proxy Extension] Realm:", details.realm);
    
    // Provide credentials immediately
    var auth = {
      authCredentials: {
        username: PROXY_USER,
        password: PROXY_PASS
      }
    };
    
    console.log("[Proxy Extension] ✅ Providing credentials for:", PROXY_USER);
    try {
      callback(auth);
    } catch(e) {
      console.error("[Proxy Extension] ❌ Callback error:", e);
    }
  }
  
  // Register listener IMMEDIATELY - before any requests
  try {
    chrome.webRequest.onAuthRequired.addListener(
      handleAuth,
      { urls: ["<all_urls>"] },
      ["blocking"]
    );
    console.log("[Proxy Extension] ✅ Auth listener registered successfully");
  } catch(e) {
    console.error("[Proxy Extension] ❌ Failed to register listener:", e);
  }
  
  console.log("[Proxy Extension] Initialization complete - ready for auth");
})();