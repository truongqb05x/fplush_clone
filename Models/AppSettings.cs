using System.Text.Json.Serialization;

namespace FPlusClone.Models
{
    public class AppSettings
    {
        // --- Cấu hình luồng & Chrome ---
        [JsonPropertyName("threadCount")]
        public int ThreadCount { get; set; } = 2;

        [JsonPropertyName("chromePerRow")]
        public int ChromePerRow { get; set; } = 3;

        [JsonPropertyName("profilePath")]
        public string ProfilePath { get; set; } = "";

        // --- Proxy ---
        [JsonPropertyName("proxyList")]
        public string ProxyList { get; set; } = "";

        [JsonPropertyName("useProxy")]
        public bool UseProxy { get; set; } = false;

        [JsonPropertyName("proxyMethod")]
        public int ProxyMethod { get; set; } = 0;

        [JsonPropertyName("kiotProxyKey")]
        public string KiotProxyKey { get; set; } = "";

        // --- Tùy chọn Chrome ---
        [JsonPropertyName("disableImageLoad")]
        public bool DisableImageLoad { get; set; } = false;

        [JsonPropertyName("hideChrome")]
        public bool HideChrome { get; set; } = false;
    }
}
