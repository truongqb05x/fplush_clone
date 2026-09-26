using FPlusClone.Models;
using FPlusClone.Views;
using System.Windows.Input;
using System.Linq;

namespace FPlusClone.ViewModels
{
    public class TabNuoiTKViewModel : BaseTabViewModel
    {
        private int _feedTime = 3;
        public int FeedTime
        {
            get => _feedTime;
            set { if (_feedTime != value) { _feedTime = value; OnPropertyChanged(); } }
        }

        private bool _isEmotionLike = true;
        public bool IsEmotionLike
        {
            get => _isEmotionLike;
            set { if (_isEmotionLike != value) { _isEmotionLike = value; OnPropertyChanged(); } }
        }

        private bool _isEmotionTym = true;
        public bool IsEmotionTym
        {
            get => _isEmotionTym;
            set { if (_isEmotionTym != value) { _isEmotionTym = value; OnPropertyChanged(); } }
        }

        private bool _isEmotionThuong;
        public bool IsEmotionThuong
        {
            get => _isEmotionThuong;
            set { if (_isEmotionThuong != value) { _isEmotionThuong = value; OnPropertyChanged(); } }
        }

        private bool _isEmotionHaha;
        public bool IsEmotionHaha
        {
            get => _isEmotionHaha;
            set { if (_isEmotionHaha != value) { _isEmotionHaha = value; OnPropertyChanged(); } }
        }

        private bool _isEmotionWow;
        public bool IsEmotionWow
        {
            get => _isEmotionWow;
            set { if (_isEmotionWow != value) { _isEmotionWow = value; OnPropertyChanged(); } }
        }

        private bool _isEmotionBuon;
        public bool IsEmotionBuon
        {
            get => _isEmotionBuon;
            set { if (_isEmotionBuon != value) { _isEmotionBuon = value; OnPropertyChanged(); } }
        }

        private bool _isEmotionPhanNo;
        public bool IsEmotionPhanNo
        {
            get => _isEmotionPhanNo;
            set { if (_isEmotionPhanNo != value) { _isEmotionPhanNo = value; OnPropertyChanged(); } }
        }

        private int _delayMin = 10;
        public int DelayMin
        {
            get => _delayMin;
            set { if (_delayMin != value) { _delayMin = value; OnPropertyChanged(); } }
        }

        private int _delayMax = 30;
        public int DelayMax
        {
            get => _delayMax;
            set { if (_delayMax != value) { _delayMax = value; OnPropertyChanged(); } }
        }

        private bool _isReadNoti = true;
        public bool IsReadNoti
        {
            get => _isReadNoti;
            set { if (_isReadNoti != value) { _isReadNoti = value; OnPropertyChanged(); } }
        }

        private int _readNotiCount = 5;
        public int ReadNotiCount
        {
            get => _readNotiCount;
            set { if (_readNotiCount != value) { _readNotiCount = value; OnPropertyChanged(); } }
        }

        private bool _isChat;
        public bool IsChat
        {
            get => _isChat;
            set { if (_isChat != value) { _isChat = value; OnPropertyChanged(); } }
        }

        private bool _isRandomClick = true;
        public bool IsRandomClick
        {
            get => _isRandomClick;
            set { if (_isRandomClick != value) { _isRandomClick = value; OnPropertyChanged(); } }
        }

        private int _maxThreads = 1;
        public int MaxThreads
        {
            get => _maxThreads;
            set { if (_maxThreads != value) { _maxThreads = value; OnPropertyChanged(); } }
        }

        private bool _isResetDcom;
        public bool IsResetDcom
        {
            get => _isResetDcom;
            set { if (_isResetDcom != value) { _isResetDcom = value; OnPropertyChanged(); } }
        }

        private int _resetDcomAfter = 5;
        public int ResetDcomAfter
        {
            get => _resetDcomAfter;
            set { if (_resetDcomAfter != value) { _resetDcomAfter = value; OnPropertyChanged(); } }
        }

        private string _logText = "";
        public string LogText
        {
            get => _logText;
            set { if (_logText != value) { _logText = value; OnPropertyChanged(); } }
        }

        private bool _isRunning;
        public bool IsRunning
        {
            get => _isRunning;
            set { if (_isRunning != value) { _isRunning = value; OnPropertyChanged(); System.Windows.Application.Current.Dispatcher.Invoke(() => System.Windows.Input.CommandManager.InvalidateRequerySuggested()); } }
        }

        private string _statusText = "Chưa chạy";
        public string StatusText
        {
            get => _statusText;
            set { if (_statusText != value) { _statusText = value; OnPropertyChanged(); } }
        }

        public ICommand StartTaskCommand { get; }
        public ICommand StopTaskCommand { get; }

        private System.Diagnostics.Process _runningProcess;

        public TabNuoiTKViewModel()
        {
            StartTaskCommand = new RelayCommand(_ => StartTask());
            StopTaskCommand = new RelayCommand(_ => StopTask());
        }

        private void StartTask()
        {
            if (IsRunning) return;

            var selectedUids = TaskAccounts.Select(t => t.Account.Uid).ToList();
            if (selectedUids.Count == 0)
            {
                System.Windows.MessageBox.Show("Vui lòng chọn ít nhất 1 tài khoản để chạy.");
                return;
            }

            var accountLines = TaskAccounts.Select(t => 
                $"{t.Account.Uid}|{t.Account.Password}|{t.Account.TwoFA}|{t.Account.Cookie}|{t.Account.Token}"
            ).ToList();

            var appSettings = SettingsViewModel.Load();
            var proxyLines = new System.Collections.Generic.List<string>();
            if (appSettings.ProxyList != null)
            {
                proxyLines = appSettings.ProxyList
                    .Split(new[] { '\r', '\n' }, System.StringSplitOptions.RemoveEmptyEntries)
                    .Where(l => !string.IsNullOrWhiteSpace(l))
                    .ToList();
            }

            var fullConfig = new
            {
                MaxThreads = MaxThreads,
                FeedTime = FeedTime,
                IsLikePost = IsEmotionLike || IsEmotionTym || IsEmotionThuong || IsEmotionHaha || IsEmotionWow || IsEmotionBuon || IsEmotionPhanNo,
                IsReactionLike = IsEmotionLike,
                IsReactionLove = IsEmotionTym,
                IsReactionCare = IsEmotionThuong,
                IsReactionHaha = IsEmotionHaha,
                IsReactionWow = IsEmotionWow,
                IsReactionSad = IsEmotionBuon,
                IsReactionAngry = IsEmotionPhanNo,
                ReactionDelayMin = DelayMin,
                ReactionDelayMax = DelayMax,
                IsReadNoti = IsReadNoti,
                ReadNotiCount = ReadNotiCount,
                IsChat = IsChat,
                IsRandomClick = IsRandomClick,
                
                IsRepeat = IsRepeat,
                RepeatCount = RepeatCount,
                
                SelectedAccounts = selectedUids,
                SelectedAccountsInfo = accountLines,
                
                ProxyMethod = appSettings.ProxyMethod,
                ProxyList = proxyLines,
                KiotProxyKey = appSettings.KiotProxyKey ?? "",
                IsResetDcom = IsResetDcom,
                ResetDcomAfter = ResetDcomAfter
            };
            
            string jsonConfig = System.Text.Json.JsonSerializer.Serialize(fullConfig);
            
            foreach (var acc in TaskAccounts)
            {
                acc.Progress = "0/1";
            }

            IsRunning = true;
            StatusText = "Đang chạy";
            LogText = "";
            
            try
            {
                _runningProcess = new System.Diagnostics.Process();
                
                string baseDir = System.AppDomain.CurrentDomain.BaseDirectory;
                string mainPyPath = System.IO.Path.Combine(baseDir, "Logic", "main.py");
                if (!System.IO.File.Exists(mainPyPath) && baseDir.Contains("bin"))
                {
                    baseDir = System.IO.Path.GetFullPath(System.IO.Path.Combine(baseDir, "..", "..", ".."));
                }

                string configPath = System.IO.Path.Combine(baseDir, "nuoitk_config.json");
                System.IO.File.WriteAllText(configPath, jsonConfig);

                _runningProcess.StartInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = $"-u Logic\\main.py 3 nuoitk_config.json", // Mode 3 is Warmup
                    WorkingDirectory = baseDir,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    StandardOutputEncoding = System.Text.Encoding.UTF8,
                    StandardErrorEncoding = System.Text.Encoding.UTF8
                };
                _runningProcess.StartInfo.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                
                _runningProcess.EnableRaisingEvents = true;
                
                string errorOutput = "";
                _runningProcess.OutputDataReceived += (s, e) => 
                {
                    if (e.Data != null)
                    {
                        System.Windows.Application.Current.Dispatcher.Invoke(() => 
                        {
                            LogText += e.Data + "\n";
                            
                            var match = System.Text.RegularExpressions.Regex.Match(e.Data, @"\[(.*?)\]\s*UI_STATUS\|Die");
                            if (match.Success)
                            {
                                string uidStr = match.Groups[1].Value.Trim();
                                var acc = TaskAccounts.FirstOrDefault(a => a.Account.Uid == uidStr);
                                if (acc != null)
                                {
                                    acc.Status = "Die";
                                }
                            }

                            // Check for UI_PROGRESS_SUCCESS
                            var progressMatch = System.Text.RegularExpressions.Regex.Match(e.Data, @"\[(.*?)\]\s*UI_PROGRESS_SUCCESS");
                            if (progressMatch.Success)
                            {
                                string uidStr = progressMatch.Groups[1].Value.Trim();
                                var acc = TaskAccounts.FirstOrDefault(a => a.Account.Uid == uidStr);
                                if (acc != null)
                                {
                                    var parts = acc.Progress.Split('/');
                                    if (parts.Length > 0 && int.TryParse(parts[0], out int currentSuccess))
                                    {
                                        acc.Progress = $"{currentSuccess + 1}/1";
                                    }
                                }
                            }
                            
                            // Check for UI_LOGIN_FAILED
                            var loginFailMatch = System.Text.RegularExpressions.Regex.Match(e.Data, @"\[(.*?)\]\s*UI_LOGIN_FAILED");
                            if (loginFailMatch.Success)
                            {
                                string uidStr = loginFailMatch.Groups[1].Value.Trim();
                                var mainVm = System.Windows.Application.Current.MainWindow?.DataContext as MainViewModel;
                                mainVm?.UpdateAccountNote(uidStr, "Login Failed");
                            }
                            
                            var removeMatch = System.Text.RegularExpressions.Regex.Match(e.Data, @"\[(.*?)\]\s*UI_REMOVE\|(.+)");
                            if (removeMatch.Success)
                            {
                                string uidStr = removeMatch.Groups[2].Value.Trim();
                                var acc = TaskAccounts.FirstOrDefault(a => a.Account.Uid == uidStr);
                                if (acc != null)
                                {
                                    TaskAccounts.Remove(acc);
                                    var mainVm = System.Windows.Application.Current.MainWindow?.DataContext as MainViewModel;
                                    mainVm?.UpdateAccountNote(uidStr, "Pending (bị từ chối/chờ duyệt)");
                                }
                            }
                        });
                    }
                };
                _runningProcess.ErrorDataReceived += (s, e) => 
                { 
                    if (e.Data != null) 
                    {
                        errorOutput += e.Data + "\n";
                        System.Windows.Application.Current.Dispatcher.Invoke(() => 
                        {
                            LogText += "[ERROR] " + e.Data + "\n";
                        });
                    }
                };
                
                _runningProcess.Exited += (s, e) => 
                {
                    System.Windows.Application.Current.Dispatcher.Invoke(() => 
                    {
                        IsRunning = false;
                        
                        if (_runningProcess != null && _runningProcess.HasExited && _runningProcess.ExitCode == 0)
                        {
                            StatusText = "Đã kết thúc";
                        }
                        else
                        {
                            StatusText = "Đã dừng";
                        }
                        
                        if (!string.IsNullOrWhiteSpace(errorOutput))
                        {
                            System.Windows.MessageBox.Show("Python Error:\n" + errorOutput);
                        }
                    });
                };
                
                _runningProcess.Start();
                _runningProcess.BeginOutputReadLine();
                _runningProcess.BeginErrorReadLine();
            }
            catch (System.Exception ex)
            {
                IsRunning = false;
                StatusText = "Lỗi";
                System.Windows.MessageBox.Show("Lỗi khởi tạo python: " + ex.Message);
            }
        }

        private void StopTask()
        {
            if (_runningProcess != null && !_runningProcess.HasExited)
            {
                try
                {
                    _runningProcess.Kill();
                }
                catch { }
            }

            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "taskkill",
                    Arguments = "/F /IM chrome.exe /T",
                    CreateNoWindow = true,
                    UseShellExecute = false
                });
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "taskkill",
                    Arguments = "/F /IM chromedriver.exe /T",
                    CreateNoWindow = true,
                    UseShellExecute = false
                });
            }
            catch { }

            IsRunning = false;
            StatusText = "Đã dừng";
        }
    }
}
