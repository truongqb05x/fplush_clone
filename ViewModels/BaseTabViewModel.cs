using FPlusClone.Models;
using FPlusClone.Views;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using System;
using System.Linq;
using System.Windows;

namespace FPlusClone.ViewModels
{
    public abstract class BaseTabViewModel : INotifyPropertyChanged
    {
        public ObservableCollection<TaskAccount> TaskAccounts { get; set; } = new ObservableCollection<TaskAccount>();

        private bool _isRepeat;
        public bool IsRepeat
        {
            get => _isRepeat;
            set { if (_isRepeat != value) { _isRepeat = value; OnPropertyChanged(); } }
        }

        private int _repeatCount = 1;
        public int RepeatCount
        {
            get => _repeatCount;
            set { if (_repeatCount != value) { _repeatCount = value; OnPropertyChanged(); } }
        }

        private bool _actionBeforePost;
        public bool ActionBeforePost
        {
            get => _actionBeforePost;
            set { if (_actionBeforePost != value) { _actionBeforePost = value; OnPropertyChanged(); } }
        }

        public ActionConfig ConfigBeforePost { get; set; } = new ActionConfig();

        private bool _actionAfterPost;
        public bool ActionAfterPost
        {
            get => _actionAfterPost;
            set { if (_actionAfterPost != value) { _actionAfterPost = value; OnPropertyChanged(); } }
        }

        public ActionConfig ConfigAfterPost { get; set; } = new ActionConfig();

        public ICommand OpenSelectAccountCommand { get; }
        public ICommand RemoveAccountCommand { get; }
        public ICommand SelectAllCommand { get; }
        public ICommand OpenActionConfigCommand { get; }

        public BaseTabViewModel()
        {
            OpenSelectAccountCommand = new RelayCommand(_ => OpenSelectAccountModal());
            OpenActionConfigCommand = new RelayCommand(obj => OpenActionConfigModal(obj as string));
            RemoveAccountCommand = new RelayCommand(obj =>
            {
                if (obj is TaskAccount acc)
                    TaskAccounts.Remove(acc);
                else
                {
                    var selected = TaskAccounts.Where(a => a.IsSelected).ToList();
                    foreach (var a in selected) TaskAccounts.Remove(a);
                }
            });

            SelectAllCommand = new RelayCommand(_ =>
            {
                bool allSelected = TaskAccounts.All(a => a.IsSelected);
                foreach (var acc in TaskAccounts) acc.IsSelected = !allSelected;
            });
        }

        private void OpenSelectAccountModal()
        {
            var mainWindow = Application.Current.MainWindow;
            var mainViewModel = mainWindow?.DataContext as MainViewModel;
            if (mainViewModel == null) return;

            var window = new Views.SelectAccountWindow(mainViewModel.Accounts)
            {
                Owner = mainWindow
            };

            if (window.ShowDialog() == true)
            {
                var appSettings = SettingsViewModel.Load();
                var proxyLines = (appSettings.ProxyList ?? "")
                    .Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)
                    .Where(l => !string.IsNullOrWhiteSpace(l))
                    .ToList();

                var existingCount = TaskAccounts.Count;
                foreach (var acc in window.SelectedAccountsResult)
                {
                    if (!TaskAccounts.Any(a => a.Account.Uid == acc.Uid))
                    {
                        string proxyLabel = "Direct";
                        if (appSettings.ProxyMethod == 1 && proxyLines.Count > 0)
                        {
                            int idx = existingCount % proxyLines.Count;
                            proxyLabel = proxyLines[idx];
                        }
                        else if (appSettings.ProxyMethod == 2)
                        {
                            proxyLabel = string.IsNullOrEmpty(appSettings.KiotProxyKey)
                                ? "KiotProxy (no key)"
                                : $"KiotProxy ({appSettings.KiotProxyKey.Substring(0, Math.Min(8, appSettings.KiotProxyKey.Length))}...)";    
                        }
                        TaskAccounts.Add(new TaskAccount { Account = acc, Proxy = proxyLabel });
                        existingCount++;
                    }
                }
            }
        }

        private void OpenActionConfigModal(string type)
        {
            var config = type == "Before" ? ConfigBeforePost : ConfigAfterPost;
            var window = new Views.ActionConfigWindow(config)
            {
                Owner = Application.Current.MainWindow
            };

            if (window.ShowDialog() == true)
            {
                if (type == "Before") ConfigBeforePost = window.Config;
                else ConfigAfterPost = window.Config;
            }
        }

        public event PropertyChangedEventHandler PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
