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

        // --- Proxy ---
        [JsonPropertyName("proxyList")]
        public string ProxyList { get; set; } = "";

        [JsonPropertyName("useProxy")]
        public bool UseProxy { get; set; } = false;

        // --- Tùy chọn Chrome ---
        [JsonPropertyName("disableImageLoad")]
        public bool DisableImageLoad { get; set; } = false;

        [JsonPropertyName("hideChrome")]
        public bool HideChrome { get; set; } = false;
    }
}
