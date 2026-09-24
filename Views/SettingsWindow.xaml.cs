using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Input;
using FPlusClone.Models;
using FPlusClone.ViewModels;

namespace FPlusClone.Views
{
    public partial class SettingsWindow : Window
    {
        public SettingsWindow()
        {
            InitializeComponent();
        }
    }

    public class SettingsViewModel : ViewModelBase
    {
        private static readonly string SettingsPath =
            Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "settings.json");

        // ── Binding properties ──────────────────────────────────────
        private int _threadCount;
        public int ThreadCount { get => _threadCount; set => SetProperty(ref _threadCount, value); }

        private int _chromePerRow;
        public int ChromePerRow { get => _chromePerRow; set => SetProperty(ref _chromePerRow, value); }

        private string _proxyList;
        public string ProxyList { get => _proxyList; set => SetProperty(ref _proxyList, value); }

        private bool _useProxy;
        public bool UseProxy { get => _useProxy; set => SetProperty(ref _useProxy, value); }

        private int _proxyMethod;
        public int ProxyMethod 
        { 
            get => _proxyMethod; 
            set 
            {
                if (SetProperty(ref _proxyMethod, value))
                {
                    OnPropertyChanged(nameof(IsStaticProxy));
                    OnPropertyChanged(nameof(IsKiotProxy));
                }
            }
        }
        
        public bool IsStaticProxy => ProxyMethod == 1;
        public bool IsKiotProxy => ProxyMethod == 2;

        private string _kiotProxyKey;
        public string KiotProxyKey { get => _kiotProxyKey; set => SetProperty(ref _kiotProxyKey, value); }

        private bool _disableImageLoad;
        public bool DisableImageLoad { get => _disableImageLoad; set => SetProperty(ref _disableImageLoad, value); }

        private bool _hideChrome;
        public bool HideChrome { get => _hideChrome; set => SetProperty(ref _hideChrome, value); }

        private string _profilePath;
        public string ProfilePath { get => _profilePath; set => SetProperty(ref _profilePath, value); }

        // ── Commands ────────────────────────────────────────────────
        public ICommand SaveCommand { get; }
        public ICommand CancelCommand { get; }
        public ICommand SelectProfilePathCommand { get; }

        public bool? DialogResult { get; private set; }
        public event Action RequestClose;

        // ── Static: load settings từ file (dùng toàn app) ──────────
        public static AppSettings Load()
        {
            try
            {
                if (File.Exists(SettingsPath))
                    return JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(SettingsPath))
                           ?? new AppSettings();
            }
            catch { }
            return new AppSettings();
        }

        public static void Save(AppSettings s)
        {
            try
            {
                File.WriteAllText(SettingsPath,
                    JsonSerializer.Serialize(s, new JsonSerializerOptions { WriteIndented = true }));
            }
            catch { }
        }

        // ── Constructor ─────────────────────────────────────────────
        public SettingsViewModel()
        {
            // Load từ file hoặc dùng default
            var s = Load();
            ThreadCount      = s.ThreadCount;
            ChromePerRow     = s.ChromePerRow;
            ProxyList        = s.ProxyList;
            UseProxy         = s.UseProxy;
            ProxyMethod      = s.ProxyMethod;
            KiotProxyKey     = s.KiotProxyKey;
            DisableImageLoad = s.DisableImageLoad;
            HideChrome       = s.HideChrome;
            ProfilePath      = s.ProfilePath;

            SaveCommand = new RelayCommand(_ =>
            {
                Save(new AppSettings
                {
                    ThreadCount      = ThreadCount,
                    ChromePerRow     = ChromePerRow,
                    ProxyList        = ProxyList ?? "",
                    UseProxy         = UseProxy,
                    ProxyMethod      = ProxyMethod,
                    KiotProxyKey     = KiotProxyKey ?? "",
                    DisableImageLoad = DisableImageLoad,
                    HideChrome       = HideChrome,
                    ProfilePath      = ProfilePath ?? ""
                });
                DialogResult = true;
                RequestClose?.Invoke();
            });

            CancelCommand = new RelayCommand(_ =>
            {
                DialogResult = false;
                RequestClose?.Invoke();
            });

            SelectProfilePathCommand = new RelayCommand(_ =>
            {
                var dialog = new Microsoft.Win32.OpenFileDialog
                {
                    ValidateNames = false,
                    CheckFileExists = false,
                    CheckPathExists = true,
                    FileName = "Folder Selection"
                };
                if (dialog.ShowDialog() == true)
                {
                    var folder = Path.GetDirectoryName(dialog.FileName);
                    if (!string.IsNullOrEmpty(folder))
                    {
                        ProfilePath = folder;
                    }
                }
            });
        }
    }
}
