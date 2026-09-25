using FPlusClone.Models;
using FPlusClone.Views;
using System.Windows.Input;
using System.Linq;

namespace FPlusClone.ViewModels
{
    public class TabSpamGroupViewModel : BaseTabViewModel
    {
        private string _groupUids;
        public string GroupUids
        {
            get => _groupUids;
            set { if (_groupUids != value) { _groupUids = value; SaveGroupUids(); OnPropertyChanged(); } }
        }

        private string _imageGroupUids;
        public string ImageGroupUids
        {
            get => _imageGroupUids;
            set { if (_imageGroupUids != value) { _imageGroupUids = value; SaveImageGroupUids(); OnPropertyChanged(); } }
        }

        private bool _isSequentialComment = true;
        public bool IsSequentialComment
        {
            get => _isSequentialComment;
            set { if (_isSequentialComment != value) { _isSequentialComment = value; OnPropertyChanged(); } }
        }

        private bool _isRandomComment;
        public bool IsRandomComment
        {
            get => _isRandomComment;
            set { if (_isRandomComment != value) { _isRandomComment = value; OnPropertyChanged(); } }
        }
        private bool _isSettingsModalOpen;
        public bool IsSettingsModalOpen
        {
            get => _isSettingsModalOpen;
            set { if (_isSettingsModalOpen != value) { _isSettingsModalOpen = value; OnPropertyChanged(); } }
        }

        private int _maxThreads = 3;
        public int MaxThreads
        {
            get => _maxThreads;
            set { if (_maxThreads != value) { _maxThreads = value; OnPropertyChanged(); } }
        }

        private string _logText = "";
        public string LogText
        {
            get => _logText;
            set { if (_logText != value) { _logText = value; OnPropertyChanged(); } }
        }

        private bool _isTextComment = true;
        public bool IsTextComment
        {
            get => _isTextComment;
            set { if (_isTextComment != value) { _isTextComment = value; OnPropertyChanged(); } }
        }

        private bool _isImageComment;
        public bool IsImageComment
        {
            get => _isImageComment;
            set { if (_isImageComment != value) { _isImageComment = value; OnPropertyChanged(); } }
        }

        private string _imageFolderPath;
        public string ImageFolderPath
        {
            get => _imageFolderPath;
            set { if (_imageFolderPath != value) { _imageFolderPath = value; OnPropertyChanged(); } }
        }

        public System.Collections.ObjectModel.ObservableCollection<CommentModel> CommentsList { get; set; } = new System.Collections.ObjectModel.ObservableCollection<CommentModel>();

        private string _newComment;
        public string NewComment
        {
            get => _newComment;
            set { if (_newComment != value) { _newComment = value; OnPropertyChanged(); } }
        }

        public ICommand AddCommentCommand { get; }
        public ICommand EditCommentCommand { get; }
        public ICommand DeleteCommentCommand { get; }

        private int _maxComments = 5;
        public int MaxComments
        {
            get => _maxComments;
            set { if (_maxComments != value) { _maxComments = value; OnPropertyChanged(); } }
        }

        private int _delayMin = 15;
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

        private bool _editAfterPost = true;
        public bool EditAfterPost
        {
            get => _editAfterPost;
            set { if (_editAfterPost != value) { _editAfterPost = value; OnPropertyChanged(); } }
        }

        private bool _isCheckApproval;
        public bool IsCheckApproval
        {
            get => _isCheckApproval;
            set { if (_isCheckApproval != value) { _isCheckApproval = value; OnPropertyChanged(); } }
        }

        private bool _isResetDcom;
        public bool IsResetDcom
        {
            get => _isResetDcom;
            set { if (_isResetDcom != value) { _isResetDcom = value; OnPropertyChanged(); } }
        }

        private int _resetDcomAfter = 2;
        public int ResetDcomAfter
        {
            get => _resetDcomAfter;
            set { if (_resetDcomAfter != value) { _resetDcomAfter = value; OnPropertyChanged(); } }
        }

        public ICommand StartTaskCommand { get; }
        public ICommand StopTaskCommand { get; }
        public ICommand SelectImageFolderCommand { get; }
        public ICommand OpenSettingsCommand { get; }
        public ICommand CloseSettingsCommand { get; }

        private readonly string commentsFilePath = "comments_spamgroup.txt";
        private readonly string groupUidsFilePath = "group_uids_spamgroup.txt";
        private readonly string imageGroupUidsFilePath = "image_group_uids_spamgroup.txt";

        public TabSpamGroupViewModel()
        {
            LoadComments();
            LoadGroupUids();
            LoadImageGroupUids();

            SelectImageFolderCommand = new RelayCommand(_ =>
            {
                var dialog = new Microsoft.Win32.OpenFolderDialog
                {
                    Title = "Chọn thư mục chứa ảnh bình luận"
                };

                if (dialog.ShowDialog() == true)
                {
                    ImageFolderPath = dialog.FolderName;
                }
            });

            StartTaskCommand = new RelayCommand(_ => StartTask());
            StopTaskCommand = new RelayCommand(_ => StopTask());
            OpenSettingsCommand = new RelayCommand(_ => IsSettingsModalOpen = true);
            CloseSettingsCommand = new RelayCommand(_ => IsSettingsModalOpen = false);

            AddCommentCommand = new RelayCommand(_ =>
            {
                if (!string.IsNullOrWhiteSpace(NewComment))
                {
                    CommentsList.Add(new CommentModel { Index = CommentsList.Count + 1, Content = NewComment });
                    SaveComments();
                    NewComment = string.Empty;
                }
            });

            DeleteCommentCommand = new RelayCommand(obj =>
            {
                if (obj is CommentModel comment)
                {
                    CommentsList.Remove(comment);
                    for (int i = 0; i < CommentsList.Count; i++)
                    {
                        CommentsList[i].Index = i + 1;
                    }
                    SaveComments();
                }
            });

            EditCommentCommand = new RelayCommand(obj =>
            {
                if (obj is CommentModel oldComment)
                {
                    var window = new Views.EditCommentWindow(oldComment.Content)
                    {
                        Owner = System.Windows.Application.Current.MainWindow
                    };

                    if (window.ShowDialog() == true)
                    {
                        string newText = window.CommentText;
                        if (!string.IsNullOrWhiteSpace(newText) && newText != oldComment.Content)
                        {
                            oldComment.Content = newText;
                            SaveComments();
                        }
                    }
                }
            });
        }

        private void LoadComments()
        {
            if (System.IO.File.Exists(commentsFilePath))
            {
                var lines = System.IO.File.ReadAllLines(commentsFilePath);
                int index = 1;
                foreach (var line in lines)
                {
                    if (!string.IsNullOrWhiteSpace(line))
                    {
                        CommentsList.Add(new CommentModel { Index = index++, Content = line });
                    }
                }
            }
        }

        private void SaveComments()
        {
            var lines = CommentsList.Select(c => c.Content).ToArray();
            System.IO.File.WriteAllLines(commentsFilePath, lines);
        }

        private void LoadGroupUids()
        {
            if (System.IO.File.Exists(groupUidsFilePath))
            {
                _groupUids = System.IO.File.ReadAllText(groupUidsFilePath);
                OnPropertyChanged(nameof(GroupUids));
            }
        }

        private void SaveGroupUids()
        {
            if (_groupUids != null)
            {
                System.IO.File.WriteAllText(groupUidsFilePath, _groupUids);
            }
        }

        private void LoadImageGroupUids()
        {
            if (System.IO.File.Exists(imageGroupUidsFilePath))
            {
                _imageGroupUids = System.IO.File.ReadAllText(imageGroupUidsFilePath);
                OnPropertyChanged(nameof(ImageGroupUids));
            }
        }

        private void SaveImageGroupUids()
        {
            if (_imageGroupUids != null)
            {
                System.IO.File.WriteAllText(imageGroupUidsFilePath, _imageGroupUids);
            }
        }

        private bool _isRunning;
        public bool IsRunning
        {
            get => _isRunning;
            set { if (_isRunning != value) { _isRunning = value; OnPropertyChanged(); System.Windows.Application.Current.Dispatcher.Invoke(() => System.Windows.Input.CommandManager.InvalidateRequerySuggested()); } }
        }

        private string _statusText;
        public string StatusText
        {
            get => _statusText;
            set { if (_statusText != value) { _statusText = value; OnPropertyChanged(); } }
        }

        private System.Diagnostics.Process _runningProcess;

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

            // Đọc cài đặt proxy từ settings.json
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
                MaxThreads = MaxThreads, // <-- Thêm số luồng
                GroupUids = GroupUids?.Split(new[] { '\r', '\n' }, System.StringSplitOptions.RemoveEmptyEntries).ToList() ?? new System.Collections.Generic.List<string>(),
                ImageGroupUids = ImageGroupUids?.Split(new[] { '\r', '\n' }, System.StringSplitOptions.RemoveEmptyEntries).ToList() ?? new System.Collections.Generic.List<string>(),
                IsTextComment = IsTextComment,
                IsImageComment = IsImageComment,
                ImageFolderPath = ImageFolderPath,
                IsSequentialComment = IsSequentialComment,
                IsRandomComment = IsRandomComment,
                CommentsList = CommentsList.Select(c => c.Content).ToList(),
                SelectedAccounts = selectedUids,
                SelectedAccountsInfo = accountLines, // <-- Truyền trực tiếp qua json
                
                // Base Tab config
                IsRepeat = IsRepeat,
                RepeatCount = RepeatCount,
                ActionBeforePost = ActionBeforePost,
                ConfigBeforePost = ConfigBeforePost,
                ActionAfterPost = ActionAfterPost,
                ConfigAfterPost = ConfigAfterPost,

                // Proxy từ cài đặt hệ thống (Settings Modal)
                ProxyMethod = appSettings.ProxyMethod,
                ProxyList = proxyLines,
                KiotProxyKey = appSettings.KiotProxyKey ?? "",

                // Reset DCOM (chỉ áp dụng khi KiotProxy)
                IsResetDcom = IsResetDcom,
                ResetDcomAfter = ResetDcomAfter
            };
            
            string jsonConfig = System.Text.Json.JsonSerializer.Serialize(fullConfig);
            System.IO.File.WriteAllText("spam_group_config.json", jsonConfig);

            IsRunning = true;
            StatusText = "Đang chạy";
            LogText = ""; // Clear log when starting
            
            try
            {
                _runningProcess = new System.Diagnostics.Process();
                
                // Tìm thư mục gốc chứa thư mục Logic
                string baseDir = System.AppDomain.CurrentDomain.BaseDirectory;
                string mainPyPath = System.IO.Path.Combine(baseDir, "Logic", "main.py");
                if (!System.IO.File.Exists(mainPyPath) && baseDir.Contains("bin"))
                {
                    // Lùi lại 3 cấp nếu đang chạy trong bin\Debug\netX.X (về thư mục main)
                    baseDir = System.IO.Path.GetFullPath(System.IO.Path.Combine(baseDir, "..", "..", ".."));
                }

                // Ghi file json vào thư mục chạy python để python chắc chắn đọc được
                string configPath = System.IO.Path.Combine(baseDir, "spam_group_config.json");
                System.IO.File.WriteAllText(configPath, jsonConfig);

                _runningProcess.StartInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = $"-u Logic\\main.py 1 spam_group_config.json",
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
                            
                            // Check for UI_STATUS|Die
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
                        
                        // Nếu tiến trình tự kết thúc thành công (ExitCode == 0)
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
