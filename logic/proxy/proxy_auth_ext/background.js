var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "http",
            host: "proxy-s1.resident-psun.io.vn",
            port: 20028
        }
    }
};

chrome.proxy.settings.set(
    { value: config, scope: "regular" },
    function() {}
);

chrome.webRequest.onAuthRequired.addListener(
    function(details) {
        return {
            authCredentials: {
                username: "sun5020028",
                password: "JbW9MMqxO63U"
            }
        };
    },
    { urls: ["<all_urls>"] },
    ["blocking"]
);
