using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Windows.Data;
using System.Windows.Input;
using FPlusClone.Models;
using FPlusClone.Views;

namespace FPlusClone.ViewModels
{
    public class MainViewModel : ViewModelBase
    {
        private ObservableCollection<FacebookAccount> _accounts = new ObservableCollection<FacebookAccount>();
        private bool _isBulkOperation = false;
        private bool _isBulkSelecting = false;  // suppress SelectedCount spam khi select all
        private readonly string _filePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "accounts.json");
        private readonly string _backupFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "accounts_deleted_backup.json");

        public ObservableCollection<FolderStat> FolderStatistics { get; } = new ObservableCollection<FolderStat>();

        public ObservableCollection<FacebookAccount> Accounts
        {
            get => _accounts;
            set
            {
                var old = _accounts;
                if (SetProperty(ref _accounts, value))
                {
                    if (old != null) old.CollectionChanged -= OnAccountsCollectionChanged;
                    if (_accounts != null) 
                    {
                        _accounts.CollectionChanged += OnAccountsCollectionChanged;
                        foreach (var acc in _accounts) acc.PropertyChanged += Account_PropertyChanged;
                    }

                    ItemsView = new ListCollectionView(_accounts ?? new ObservableCollection<FacebookAccount>());
                    ItemsView.Filter = FilterAccounts;
                    OnPropertyChanged(nameof(ItemsView));
                }
            }
        }

        private void OnAccountsCollectionChanged(object sender, NotifyCollectionChangedEventArgs e)
        {
            if (e.NewItems != null)
            {
                foreach (FacebookAccount item in e.NewItems) 
                    item.PropertyChanged += Account_PropertyChanged;
            }
            if (e.OldItems != null)
            {
                foreach (FacebookAccount item in e.OldItems)
                    item.PropertyChanged -= Account_PropertyChanged;
            }
            
            if (!_isBulkOperation)
            {
                SaveAccounts();
                UpdateFolderStatistics();
                OnPropertyChanged(nameof(SelectedCount));
                ItemsView?.Refresh();
            }
        }

        public ICollectionView ItemsView { get; private set; }
        public int SelectedCount => Accounts?.Count(a => a.IsSelected) ?? 0;

        // ChromeTabs: các tab con thuộc Chrome Manager
        public ObservableCollection<TabViewModel> ChromeTabs { get; set; }
        public ObservableCollection<AppFunction> AvailableFunctions { get; set; }
        public ObservableCollection<string> Folders { get; set; }
        public ObservableCollection<string> Statuses { get; set; }

        private TabViewModel _selectedTab;
        public TabViewModel SelectedTab
        {
            get => _selectedTab;
            set
            {
                if (SetProperty(ref _selectedTab, value))
                {
                    OnPropertyChanged(nameof(IsAccountTabSelected));
                    OnPropertyChanged(nameof(IsChromeFunctionTabActive));
                    if (ChromeTabs != null)
                    {
                        foreach (var tab in ChromeTabs)
                        {
                            tab.IsSelected = (tab == value);
                        }
                    }
                }
            }
        }

        // True khi Chrome Manager đang active VÀ tab "Quản lí tài khoản Fb" đang được chọn
        public bool IsAccountTabSelected => IsChromeSelected && SelectedTab?.Header == "Quản lí tài khoản Fb";

        // True khi Chrome Manager đang active VÀ đang ở tab chức năng (không phải tab tài khoản)
        public bool IsChromeFunctionTabActive => IsChromeSelected && SelectedTab != null && SelectedTab.Header != "Quản lí tài khoản Fb";

        private bool _isHomeSelected = true;
        public bool IsHomeSelected { get => _isHomeSelected; set => SetProperty(ref _isHomeSelected, value); }

        private bool _isChromeSelected;
        public bool IsChromeSelected { get => _isChromeSelected; set => SetProperty(ref _isChromeSelected, value); }

        private bool _isTokenSelected;
        public bool IsTokenSelected { get => _isTokenSelected; set => SetProperty(ref _isTokenSelected, value); }

        private void ResetMainNav()
        {
            IsHomeSelected = false;
            IsChromeSelected = false;
            IsTokenSelected = false;
        }

        private bool _isDebugConsoleVisible;
        public bool IsDebugConsoleVisible { get => _isDebugConsoleVisible; set => SetProperty(ref _isDebugConsoleVisible, value); }
        public ObservableCollection<string> DebugLogs { get; set; }

        private bool _showAddTabModal;
        public bool ShowAddTabModal { get => _showAddTabModal; set => SetProperty(ref _showAddTabModal, value); }

        private AppFunction _selectedFunction;
        public AppFunction SelectedFunction { get => _selectedFunction; set => SetProperty(ref _selectedFunction, value); }

        private string _selectedFolder = "All Folder";
        public string SelectedFolder { get => _selectedFolder; set { if (SetProperty(ref _selectedFolder, value)) ItemsView?.Refresh(); } }

        private string _selectedStatus = "All Status";
        public string SelectedStatus { get => _selectedStatus; set { if (SetProperty(ref _selectedStatus, value)) ItemsView?.Refresh(); } }

        private string _searchText;
        public string SearchText { get => _searchText; set { if (SetProperty(ref _searchText, value)) ItemsView?.Refresh(); } }

        private bool _showAddFolderInput;
        public bool ShowAddFolderInput { get => _showAddFolderInput; set => SetProperty(ref _showAddFolderInput, value); }

        private string _newFolderName;
        public string NewFolderName { get => _newFolderName; set => SetProperty(ref _newFolderName, value); }

        private bool _isLoading;
        public bool IsLoading { get => _isLoading; set => SetProperty(ref _isLoading, value); }

        private int _progressCurrent;
        public int ProgressCurrent { get => _progressCurrent; set => SetProperty(ref _progressCurrent, value); }

        private int _progressTotal;
        public int ProgressTotal { get => _progressTotal; set => SetProperty(ref _progressTotal, value); }

        private string _progressMessage = "Đang xử lý...";
        public string ProgressMessage { get => _progressMessage; set => SetProperty(ref _progressMessage, value); }

        public ICommand ToggleModalCommand { get; }
        public ICommand AddTabCommand { get; }
        public ICommand CloseTabCommand { get; }
        public ICommand SelectTabCommand { get; }
        public ICommand SearchCommand { get; }
        public ICommand SelectAllCommand { get; }
        public ICommand SelectErrorCommand { get; }
        public ICommand ToggleAddFolderCommand { get; }
        public ICommand ConfirmAddFolderCommand { get; }
        public ICommand ShowHomeCommand { get; }
        public ICommand ShowChromeCommand { get; }
        public ICommand ShowTokenCommand { get; }
        public ICommand ToggleDebugConsoleCommand { get; }
        public ICommand ShowImportAccountCommand { get; }
        public ICommand ImportFromFileCommand { get; }
        public ICommand DeleteFolderCommand { get; }
        public ICommand DeleteSelectedAccountsCommand { get; }
        public ICommand DeleteAllAccountsCommand { get; }
        public ICommand ShowCopyCustomCommand { get; }
        public ICommand CopyAccountsCommand { get; }
        public ICommand BulkEditCommand { get; }
        public ICommand ShowSettingsCommand { get; }

        public MainViewModel()
        {
            _accounts = new ObservableCollection<FacebookAccount>();
            _accounts.CollectionChanged += OnAccountsCollectionChanged;
            ItemsView = new ListCollectionView(_accounts);
            ItemsView.Filter = FilterAccounts;

            Folders = new ObservableCollection<string>();
            // ChromeTabs: chỉ hiển thị khi Chrome Manager được chọn
            ChromeTabs = new ObservableCollection<TabViewModel> { new TabViewModel { Header = "Quản lí tài khoản Fb" } };
            AvailableFunctions = new ObservableCollection<AppFunction>
            {
                new AppFunction { Name = "Comment like group",  Description = "Tự động comment hàng loạt vào các Group Facebook theo danh sách." },
                new AppFunction { Name = "Tham gia nhóm",       Description = "Tìm kiếm và tham gia nhóm theo danh sách ID/link." },
                new AppFunction { Name = "Rời nhóm",            Description = "Tự động rời thoát khỏi các Group Facebook." },
                new AppFunction { Name = "Nuôi tài khoản",      Description = "Scroll News Feed, tương tác tự nhiên để warm-up tài khoản." },
                new AppFunction { Name = "Spam Keyword",        Description = "Tìm bài viết theo từ khóa và tự động comment hàng loạt." },
                new AppFunction { Name = "Comment Page",        Description = "Tự động comment vào bài viết của các Fanpage theo ID." },
            };

            Statuses = new ObservableCollection<string> { "All Status", "Live", "Confirm Email", "Checkpoint" };
            DebugLogs = new ObservableCollection<string>
            {
                $"[{DateTime.Now:HH:mm:ss}] Application started successfully.",
                $"[{DateTime.Now:HH:mm:ss}] Version 4.9.0.7 loaded.",
                $"[{DateTime.Now:HH:mm:ss}] User interface initialized."
            };

            ToggleModalCommand = new RelayCommand(_ => ShowAddTabModal = !ShowAddTabModal);

            ShowSettingsCommand = new RelayCommand(_ =>
            {
                var vm = new Views.SettingsViewModel();
                var win = new Views.SettingsWindow
                {
                    DataContext = vm,
                    Owner = System.Windows.Application.Current.MainWindow
                };
                vm.RequestClose += () =>
                {
                    try { win.DialogResult = vm.DialogResult; } catch { }
                    win.Close();
                };
                if (win.ShowDialog() == true)
                    Log($"System: Settings saved.");
            });

            SelectTabCommand = new RelayCommand(obj =>
            {
                if (obj is TabViewModel tab)
                {
                    SelectedTab = tab;
                    // Giữ IsChromeSelected = true khi chọn tab trong Chrome Manager
                    IsChromeSelected = true;
                    IsHomeSelected = false;
                    IsTokenSelected = false;
                    OnPropertyChanged(nameof(IsAccountTabSelected));
                }
            });
            AddTabCommand = new RelayCommand(param =>
            {
                if (param is AppFunction func)
                {
                    SelectedFunction = func;
                }

                if (SelectedFunction != null && !string.IsNullOrEmpty(SelectedFunction.Name))
                {
                    if (!ChromeTabs.Any(t => t.Header == SelectedFunction.Name))
                    {
                        var newTab = new TabViewModel { Header = SelectedFunction.Name };
                        ChromeTabs.Add(newTab);
                        SelectedTab = newTab;
                        IsChromeSelected = true;
                        Log($"System: Added new Chrome tab '{SelectedFunction.Name}'.");
                    }
                    else
                    {
                        SelectedTab = ChromeTabs.First(t => t.Header == SelectedFunction.Name);
                        IsChromeSelected = true;
                    }
                    ShowAddTabModal = false;
                    ShowAddTabModal = false;
                    SelectedFunction = new AppFunction { Name = "", Description = "" };
                }
            });


            SearchCommand = new RelayCommand(_ => ItemsView?.Refresh());

            SelectAllCommand = new RelayCommand(_ =>
            {
                // Snapshot để tránh race condition
                var snapshot = Accounts.ToList();
                _isBulkSelecting = true;

                System.Threading.Tasks.Task.Run(() =>
                {
                    // Background thread: set trực tiếp vào field, KHÔNG trigger WPF binding
                    foreach (var acc in snapshot)
                        acc.SetSelectedSilently(true);
                }).ContinueWith(_ =>
                {
                    // Quay lại UI thread: chỉ refresh 1 lần duy nhất
                    _isBulkSelecting = false;
                    ItemsView?.Refresh();                        // DataGrid re-read IsSelected từ data
                    OnPropertyChanged(nameof(SelectedCount));    // Cập nhật số đã chọn
                }, System.Threading.Tasks.TaskScheduler.FromCurrentSynchronizationContext());
            });

            SelectErrorCommand = new RelayCommand(_ =>
            {
                var snapshot = Accounts.ToList();
                _isBulkSelecting = true;

                System.Threading.Tasks.Task.Run(() =>
                {
                    foreach (var acc in snapshot)
                        acc.SetSelectedSilently(acc.Status != "Live");
                }).ContinueWith(_ =>
                {
                    _isBulkSelecting = false;
                    ItemsView?.Refresh();
                    OnPropertyChanged(nameof(SelectedCount));
                }, System.Threading.Tasks.TaskScheduler.FromCurrentSynchronizationContext());
            });


            ToggleAddFolderCommand = new RelayCommand(_ => ShowAddFolderInput = !ShowAddFolderInput);

            ConfirmAddFolderCommand = new RelayCommand(_ =>
            {
                if (!string.IsNullOrWhiteSpace(NewFolderName))
                {
                    string folder = NewFolderName.Trim();
                    if (!Folders.Contains(folder))
                    {
                        Folders.Add(folder);
                        SelectedFolder = folder;
                        UpdateFolderStatistics();
                        Log($"System: New folder '{folder}' created.");
                    }
                    NewFolderName = string.Empty;
                    ShowAddFolderInput = false;
                }
            });

            DeleteFolderCommand = new RelayCommand(_ =>
            {
                if (SelectedFolder != "All Folder" && Folders.Contains(SelectedFolder))
                {
                    var result = System.Windows.MessageBox.Show(
                        $"Bạn có chắc chắn muốn xóa thư mục '{SelectedFolder}' không?\n(Tài khoản trong thư mục này sẽ được chuyển về 'default')",
                        "Xác nhận xóa thư mục",
                        System.Windows.MessageBoxButton.YesNo,
                        System.Windows.MessageBoxImage.Warning);

                    if (result == System.Windows.MessageBoxResult.Yes)
                    {
                        string folderToDelete = SelectedFolder;
                        foreach (var acc in Accounts.Where(a => a.Folder == folderToDelete)) { acc.Folder = "default"; }
                        Folders.Remove(folderToDelete);
                        SelectedFolder = "All Folder";
                        SaveAccounts();
                        UpdateFolderStatistics();
                        Log($"System: Folder '{folderToDelete}' deleted. Accounts moved to 'default'.");
                    }
                }
            });

            DeleteSelectedAccountsCommand = new RelayCommand(obj =>
            {
                if (obj is IList selectedItems)
                {
                    var itemsToRemove = selectedItems.Cast<FacebookAccount>().Distinct().ToList();
                    if (itemsToRemove.Count > 0)
                    {
                        var result = System.Windows.MessageBox.Show(
                            $"Bạn có chắc chắn muốn xóa {itemsToRemove.Count} tài khoản đã chọn không?",
                            "Xác nhận xóa",
                            System.Windows.MessageBoxButton.YesNo,
                            System.Windows.MessageBoxImage.Question);

                        if (result == System.Windows.MessageBoxResult.Yes)
                        {
                            BackupDeletedAccounts(itemsToRemove, "Xóa chọn");
                            _isBulkOperation = true;
                            IsLoading = true;
                            ProgressMessage = "Đang xóa tài khoản...";
                            ProgressTotal = itemsToRemove.Count;
                            ProgressCurrent = 0;

                            System.Threading.Tasks.Task.Run(() =>
                            {
                                try
                                {
                                    for (int i = 0; i < itemsToRemove.Count; i++)
                                    {
                                        var acc = itemsToRemove[i];
                                        System.Windows.Application.Current.Dispatcher.Invoke(() =>
                                        {
                                            Accounts.Remove(acc);
                                            ProgressCurrent = i + 1;
                                        });
                                        if (itemsToRemove.Count < 100) System.Threading.Thread.Sleep(5);
                                    }
                                }
                                finally
                                {
                                    System.Windows.Application.Current.Dispatcher.Invoke(() =>
                                    {
                                        _isBulkOperation = false;
                                        IsLoading = false;
                                        SaveAccounts();
                                        UpdateFolderStatistics();
                                        OnPropertyChanged(nameof(SelectedCount));
                                        ItemsView?.Refresh();
                                        Log($"System: Deleted {itemsToRemove.Count} highlighted accounts.");
                                    });
                                }
                            });
                        }
                    }
                }
            });

            DeleteAllAccountsCommand = new RelayCommand(_ =>
            {
                bool isAllFolder = SelectedFolder == "All Folder" || string.IsNullOrEmpty(SelectedFolder);
                var accountsToDelete = isAllFolder
                    ? Accounts.ToList()
                    : Accounts.Where(a => a.Folder == SelectedFolder).ToList();

                if (accountsToDelete.Count == 0) return;

                string warningMsg = isAllFolder
                    ? $"Bạn sắp xóa TOÀN BỘ {accountsToDelete.Count} tài khoản trên tất cả folder.\n\nSau khi xóa, dữ liệu sẽ không thể khôi phục qua ứng dụng."
                    : $"Bạn sắp xóa tất cả {accountsToDelete.Count} tài khoản trong folder:\n\n   📁 {SelectedFolder}\n\nSau khi xóa, dữ liệu sẽ không thể khôi phục qua ứng dụng.";

                var dialog = new Views.DangerConfirmDialog(warningMsg, System.Windows.Application.Current.MainWindow);
                dialog.ShowDialog();

                if (dialog.Confirmed)
                {
                    BackupDeletedAccounts(accountsToDelete, isAllFolder ? "Xóa tất cả" : $"Xóa folder '{SelectedFolder}'");
                    foreach (var acc in accountsToDelete)
                        Accounts.Remove(acc);
                    SaveAccounts();
                    UpdateFolderStatistics();
                    Log(isAllFolder
                        ? "System: Deleted all accounts."
                        : $"System: Deleted all accounts in folder '{SelectedFolder}'.");
                }
            });

            ShowCopyCustomCommand = new RelayCommand(obj =>
            {
                if (obj is IList selectedList)
                {
                    var selected = selectedList.Cast<FacebookAccount>().ToList();
                    if (selected.Count == 0) return;
                    new Views.CopyCustomWindow(new CopyCustomViewModel(selected)) { Owner = System.Windows.Application.Current.MainWindow }.ShowDialog();
                }
            });

            CopyAccountsCommand = new RelayCommand(obj =>
            {
                if (obj is object[] parameters && parameters.Length == 2)
                {
                    string format = parameters[0] as string;
                    var selected = (parameters[1] as IList)?.Cast<FacebookAccount>().ToList();
                    if (selected == null || selected.Count == 0 || string.IsNullOrEmpty(format)) return;
                    var sb = new StringBuilder();
                    foreach (var acc in selected) sb.AppendLine(FormatAccountSimple(acc, format));
                    System.Windows.Clipboard.SetText(sb.ToString());
                    Log($"System: Copied {selected.Count} accounts in format '{format}'.");
                }
            });

            BulkEditCommand = new RelayCommand(param => BulkEdit(param));

            CloseTabCommand = new RelayCommand(obj =>
            {
                if (obj is TabViewModel tabToRemove && tabToRemove.Header != "Quản lí tài khoản Fb")
                {
                    ChromeTabs.Remove(tabToRemove);
                    Log($"System: Tab '{tabToRemove.Header}' closed.");
                    if (SelectedTab == tabToRemove && ChromeTabs.Count > 0) SelectedTab = ChromeTabs[0];
                }
            });

            ShowImportAccountCommand = new RelayCommand(_ =>
            {
                var vm = new ImportAccountViewModel();
                vm.AccountsImported += (newAccounts) => MergeAccounts(newAccounts.ToList());
                new Views.ImportAccountWindow(vm) { Owner = System.Windows.Application.Current.MainWindow }.ShowDialog();
            });

            ImportFromFileCommand = new RelayCommand(_ =>
            {
                var dialog = new Microsoft.Win32.OpenFileDialog { Filter = "Text files (*.txt)|*.txt|All files (*.*)|*.*" };
                if (dialog.ShowDialog() == true)
                {
                    try
                    {
                        string content = File.ReadAllText(dialog.FileName);
                        var vm = new ImportAccountViewModel { RawData = content };
                        vm.AccountsImported += (newAccounts) => {
                            MergeAccounts(newAccounts.ToList());
                            Log($"System: Imported from file '{Path.GetFileName(dialog.FileName)}'.");
                        };
                        new Views.ImportAccountWindow(vm) { Owner = System.Windows.Application.Current.MainWindow }.ShowDialog();
                    }
                    catch (Exception ex) { Log($"Error: {ex.Message}"); }
                }
            });

            ShowHomeCommand = new RelayCommand(_ =>
            {
                ResetMainNav();
                IsHomeSelected = true;
                SelectedTab = null;
            });
            ShowChromeCommand = new RelayCommand(_ =>
            {
                ResetMainNav();
                IsChromeSelected = true;
                // Tự động chọn tab đầu tiên trong ChromeTabs (Quản lí tài khoản Fb)
                if (ChromeTabs != null && ChromeTabs.Count > 0)
                {
                    SelectedTab = ChromeTabs[0];
                    foreach (var t in ChromeTabs) t.IsSelected = (t == SelectedTab);
                }
                OnPropertyChanged(nameof(IsAccountTabSelected));
            });
            ShowTokenCommand = new RelayCommand(_ =>
            {
                ResetMainNav();
                IsTokenSelected = true;
                SelectedTab = null;
            });
            ToggleDebugConsoleCommand = new RelayCommand(_ => { IsDebugConsoleVisible = !IsDebugConsoleVisible; });

            LoadAccounts();
            if (Folders == null || Folders.Count == 0)
            {
                Folders = new ObservableCollection<string> { "All Folder", "dethiocphan", "default" };
                SaveAccounts();
            }
            Folders.CollectionChanged += (s, e) => SaveAccounts();
        }

        private void Log(string message)
        {
            DebugLogs.Insert(0, $"[{DateTime.Now:HH:mm:ss}] {message}");
            if (DebugLogs.Count > 100) DebugLogs.RemoveAt(100);
        }

        private bool FilterAccounts(object obj)
        {
            if (obj is FacebookAccount acc)
            {
                bool folderMatch = SelectedFolder == "All Folder" || acc.Folder == SelectedFolder;
                bool statusMatch = SelectedStatus == "All Status" || acc.Status == SelectedStatus;
                if (string.IsNullOrEmpty(SearchText)) return folderMatch && statusMatch;
                var terms = SearchText.Split(new[] { '\r', '\n', ',', ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries).Select(t => t.Trim().ToLower());
                bool textMatch = false;
                foreach (var term in terms)
                {
                    if ((acc.Name?.ToLower().Contains(term) ?? false) || (acc.Uid?.ToLower().Contains(term) ?? false) || (acc.UserName?.ToLower().Contains(term) ?? false) || (acc.Status?.ToLower().Contains(term) ?? false) || (acc.Note?.ToLower().Contains(term) ?? false))
                    {
                        textMatch = true; break;
                    }
                }
                return folderMatch && statusMatch && (terms.Any() ? textMatch : true);
            }
            return false;
        }

        private void Account_PropertyChanged(object sender, PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(FacebookAccount.IsSelected))
            {
                // Bỏ qua khi đang bulk select — sẽ fire 1 lần sau khi xong
                if (!_isBulkSelecting) OnPropertyChanged(nameof(SelectedCount));
            }
            else if (!_isBulkOperation)
            {
                SaveAccounts();
                if (e.PropertyName == nameof(FacebookAccount.Folder)) UpdateFolderStatistics();
            }
        }

        private void UpdateFolderStatistics()
        {
            if (_isBulkOperation || Accounts == null || Folders == null) return;
            var counts = Accounts.GroupBy(a => a.Folder ?? "default").ToDictionary(g => g.Key, g => g.Count());
            var stats = Folders.Where(f => f != "All Folder").Select(f => new FolderStat { Name = f, Count = counts.ContainsKey(f) ? counts[f] : 0 }).OrderBy(s => s.Name).ToList();
            System.Windows.Application.Current.Dispatcher.Invoke(() => {
                FolderStatistics.Clear();
                foreach (var stat in stats) FolderStatistics.Add(stat);
            });
        }

        private void SaveAccounts()
        {
            if (_isBulkOperation) return;
            try
            {
                var state = new AppDataState { Accounts = Accounts, Folders = Folders };
                File.WriteAllText(_filePath, JsonSerializer.Serialize(state, new JsonSerializerOptions { WriteIndented = true }));
            }
            catch (Exception ex) { Log($"Error saving data: {ex.Message}"); }
        }

        /// <summary>
        /// Lưu danh sách tài khoản bị xóa vào file backup riêng (append, không ghi đè).
        /// Mỗi bản ghi kèm thời điểm xóa và lý do để dễ khôi phục.
        /// </summary>
        private void BackupDeletedAccounts(List<FacebookAccount> accounts, string reason)
        {
            if (accounts == null || accounts.Count == 0) return;
            try
            {
                // Đọc dữ liệu cũ nếu file đã tồn tại
                var existingRecords = new List<DeletedAccountRecord>();
                if (File.Exists(_backupFilePath))
                {
                    try
                    {
                        var raw = File.ReadAllText(_backupFilePath);
                        existingRecords = JsonSerializer.Deserialize<List<DeletedAccountRecord>>(raw)
                                          ?? new List<DeletedAccountRecord>();
                    }
                    catch { /* file lỗi thì bắt đầu list mới */ }
                }

                // Append các bản ghi mới
                var now = DateTime.Now;
                foreach (var acc in accounts)
                {
                    existingRecords.Add(new DeletedAccountRecord
                    {
                        DeletedAt = now,
                        Reason = reason,
                        Account = acc
                    });
                }

                File.WriteAllText(_backupFilePath,
                    JsonSerializer.Serialize(existingRecords, new JsonSerializerOptions { WriteIndented = true }));

                Log($"System: Backed up {accounts.Count} deleted account(s) → accounts_deleted_backup.json");
            }
            catch (Exception ex) { Log($"Error backing up deleted accounts: {ex.Message}"); }
        }

        private string FormatAccountSimple(FacebookAccount acc, string format)
        {
            switch (format)
            {
                case "UID": return acc.Uid;
                case "Pass": return acc.Password;
                case "UID|Pass": return $"{acc.Uid}|{acc.Password}";
                case "Cookie": return acc.Cookie;
                case "Token": return acc.Token;
                case "UID|Pass|Cookie": return $"{acc.Uid}|{acc.Password}|{acc.Cookie}";
                case "UID|Pass|2FA": return $"{acc.Uid}|{acc.Password}|{acc.TwoFA}";
                case "User|Pass|2FA": return $"{acc.UserName}|{acc.Password}|{acc.TwoFA}";
                case "Full": return $"{acc.Uid}|{acc.Password}|{acc.Cookie}|{acc.Token}|{acc.TwoFA}|{acc.Proxy}";
                default: return acc.Uid;
            }
        }

        private void BulkEdit(object parameter)
        {
            if (parameter is not object[] values || values.Length < 2) return;
            string field = values[0] as string;
            var selectedItems = values[1] as IList;
            if (selectedItems == null || selectedItems.Count == 0 || string.IsNullOrEmpty(field)) return;
            var firstAcc = selectedItems[0] as FacebookAccount;
            if (firstAcc == null) return;

            // Trường hợp đặc biệt: Folder → dùng dialog chọn folder có sẵn
            if (field == "Folder")
            {
                // Lọc bỏ "All Folder" để không cho chuyển vào đó
                var selectableFolders = Folders.Where(f => f != "All Folder").ToList();
                if (selectableFolders.Count == 0)
                {
                    System.Windows.MessageBox.Show("Chưa có thư mục nào. Hãy tạo thư mục trước.", "Thông báo",
                        System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
                    return;
                }

                var folderVm = new Views.SelectFolderViewModel(
                    selectableFolders,
                    firstAcc.Folder ?? "default",
                    selectedItems.Count);

                var folderWin = new Views.SelectFolderWindow
                {
                    DataContext = folderVm,
                    Owner = System.Windows.Application.Current.MainWindow
                };
                folderVm.RequestClose += () =>
                {
                    try { folderWin.DialogResult = folderVm.DialogResult; } catch { }
                    folderWin.Close();
                };

                if (folderWin.ShowDialog() == true && !string.IsNullOrEmpty(folderVm.SelectedFolder))
                {
                    string newFolder = folderVm.SelectedFolder;
                    foreach (FacebookAccount acc in selectedItems)
                        acc.Folder = newFolder;
                    SaveAccounts();
                    UpdateFolderStatistics();
                    Log($"System: Moved {selectedItems.Count} accounts to folder '{newFolder}'.");
                }
                return;
            }

            // Các field khác: dùng EditValueWindow bình thường
            string initialValue = "";
            switch (field)
            {
                case "UserName": initialValue = firstAcc.UserName; break;
                case "Password": initialValue = firstAcc.Password; break;
                case "Cookie": initialValue = firstAcc.Cookie; break;
                case "Token": initialValue = firstAcc.Token; break;
                case "Proxy": initialValue = firstAcc.Proxy; break;
                case "2FA": initialValue = firstAcc.TwoFA; break;
                case "Note": initialValue = firstAcc.Note; break;
                case "UserAgent": initialValue = firstAcc.UserAgent; break;
                case "Email": initialValue = firstAcc.Email; break;
                case "PassEmail": initialValue = firstAcc.PassEmail; break;
            }

            var vm = new EditValueViewModel($"Sửa {field}", $"Nhập {field} mới:", initialValue);
            var win = new EditValueWindow { DataContext = vm, Owner = System.Windows.Application.Current.MainWindow };
            vm.RequestClose += () => { try { win.DialogResult = vm.DialogResult; } catch { } win.Close(); };

            if (win.ShowDialog() == true)
            {
                string newValue = vm.Value;
                foreach (FacebookAccount acc in selectedItems)
                {
                    switch (field)
                    {
                        case "UserName": acc.UserName = newValue; break;
                        case "Password": acc.Password = newValue; break;
                        case "Cookie": acc.Cookie = newValue; break;
                        case "Token": acc.Token = newValue; break;
                        case "Proxy": acc.Proxy = newValue; break;
                        case "2FA": acc.TwoFA = newValue; break;
                        case "Note": acc.Note = newValue; break;
                        case "UserAgent": acc.UserAgent = newValue; break;
                        case "Email": acc.Email = newValue; break;
                        case "PassEmail": acc.PassEmail = newValue; break;
                    }
                }
                SaveAccounts();
                Log($"System: Bulk edited '{field}' for {selectedItems.Count} items.");
            }
        }


        private void MergeAccounts(List<FacebookAccount> newAccounts)
        {
            string targetFolder = (SelectedFolder != "All Folder" && !string.IsNullOrEmpty(SelectedFolder)) ? SelectedFolder : "default";
            foreach (var acc in newAccounts) acc.Folder = targetFolder;
            var duplicates = new List<(FacebookAccount existing, FacebookAccount incoming)>();
            foreach (var newAcc in newAccounts)
            {
                var existing = Accounts.FirstOrDefault(a => (!string.IsNullOrEmpty(a.Uid) && a.Uid == newAcc.Uid) || (!string.IsNullOrEmpty(a.UserName) && a.UserName == newAcc.UserName));
                if (existing != null) duplicates.Add((existing, newAcc));
            }
            if (duplicates.Count > 0)
            {
                if (System.Windows.MessageBox.Show($"Lọc trùng: {duplicates.Count} tài khoản đã tồn tại. Có muốn ghi đè?", "Lọc trùng", System.Windows.MessageBoxButton.YesNo) == System.Windows.MessageBoxResult.Yes)
                {
                    foreach (var pair in duplicates) UpdateAccountData(pair.existing, pair.incoming);
                }
                var dupIncomings = duplicates.Select(d => d.incoming).ToList();
                newAccounts.RemoveAll(acc => dupIncomings.Contains(acc));
            }

            _isBulkOperation = true; IsLoading = true; ProgressMessage = "Đang thêm..."; ProgressTotal = newAccounts.Count; ProgressCurrent = 0;
            System.Threading.Tasks.Task.Run(() =>
            {
                try
                {
                    int startIdx = 0;
                    System.Windows.Application.Current.Dispatcher.Invoke(() => startIdx = Accounts.Count);
                    for (int i = 0; i < newAccounts.Count; i++)
                    {
                        var acc = newAccounts[i]; acc.Index = startIdx + i + 1;
                        System.Windows.Application.Current.Dispatcher.Invoke(() => { Accounts.Add(acc); ProgressCurrent = i + 1; });
                        if (newAccounts.Count < 100) System.Threading.Thread.Sleep(5);
                    }
                }
                finally
                {
                    System.Windows.Application.Current.Dispatcher.Invoke(() => { _isBulkOperation = false; IsLoading = false; SaveAccounts(); UpdateFolderStatistics(); OnPropertyChanged(nameof(SelectedCount)); ItemsView?.Refresh(); Log($"System: Added {newAccounts.Count} accounts."); });
                }
            });
        }

        private void UpdateAccountData(FacebookAccount existing, FacebookAccount incoming)
        {
            if (!string.IsNullOrEmpty(incoming.Password)) existing.Password = incoming.Password;
            if (!string.IsNullOrEmpty(incoming.Cookie)) existing.Cookie = incoming.Cookie;
            if (!string.IsNullOrEmpty(incoming.Token)) existing.Token = incoming.Token;
            if (!string.IsNullOrEmpty(incoming.TwoFA)) existing.TwoFA = incoming.TwoFA;
            if (!string.IsNullOrEmpty(incoming.Proxy)) existing.Proxy = incoming.Proxy;
            if (!string.IsNullOrEmpty(incoming.Note)) existing.Note = incoming.Note;
            if (!string.IsNullOrEmpty(incoming.Name)) existing.Name = incoming.Name;
        }

        private void LoadAccounts()
        {
            try
            {
                if (File.Exists(_filePath))
                {
                    var state = JsonSerializer.Deserialize<AppDataState>(File.ReadAllText(_filePath));
                    if (state?.Accounts != null) 
                    {
                        foreach (var acc in state.Accounts) acc.IsSelected = false;
                        Accounts = state.Accounts;
                    }

                    if (state?.Folders != null) Folders = state.Folders;
                    UpdateFolderStatistics();
                }
            }
            catch (Exception ex) { Log($"Error: {ex.Message}"); }
        }

        public class AppDataState
        {
            public ObservableCollection<FacebookAccount> Accounts { get; set; } = new ObservableCollection<FacebookAccount>();
            public ObservableCollection<string> Folders { get; set; } = new ObservableCollection<string>();
        }
    }

    public class FolderStat : ViewModelBase
    {
        private string _name; public string Name { get => _name; set => SetProperty(ref _name, value); }
        private int _count; public int Count { get => _count; set => SetProperty(ref _count, value); }
    }

    /// <summary>
    /// Bản ghi lưu tài khoản đã bị xóa kèm thời điểm và lý do xóa.
    /// Được append vào file accounts_deleted_backup.json để phục hồi khi cần.
    /// </summary>
    public class DeletedAccountRecord
    {
        public DateTime DeletedAt { get; set; }
        public string Reason { get; set; }
        public FacebookAccount Account { get; set; }
    }
}
