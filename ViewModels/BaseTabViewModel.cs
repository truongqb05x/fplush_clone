using FPlusClone.Models;
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

        private bool _actionAfterPost;
        public bool ActionAfterPost
        {
            get => _actionAfterPost;
            set { if (_actionAfterPost != value) { _actionAfterPost = value; OnPropertyChanged(); } }
        }

        public ICommand OpenSelectAccountCommand { get; }
        public ICommand RemoveAccountCommand { get; }
        public ICommand SelectAllCommand { get; }

        public BaseTabViewModel()
        {
            OpenSelectAccountCommand = new RelayCommand(_ => OpenSelectAccountModal());
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
            // Will implement later
            MessageBox.Show("Modal Chọn Tài Khoản - Sẽ mở SelectAccountWindow");
        }

        public event PropertyChangedEventHandler PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
