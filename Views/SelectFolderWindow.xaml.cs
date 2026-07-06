using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Input;
using FPlusClone.ViewModels;

namespace FPlusClone.Views
{
    public partial class SelectFolderWindow : Window
    {
        public SelectFolderWindow()
        {
            InitializeComponent();
        }
    }

    public class SelectFolderViewModel : ViewModelBase
    {
        private string _selectedFolder;
        public string SelectedFolder
        {
            get => _selectedFolder;
            set => SetProperty(ref _selectedFolder, value);
        }

        public IEnumerable<string> AvailableFolders { get; }
        public int AccountCount { get; }

        public bool? DialogResult { get; private set; }
        public event Action RequestClose;

        public ICommand ConfirmCommand { get; }
        public ICommand CancelCommand { get; }

        public SelectFolderViewModel(IEnumerable<string> availableFolders, string currentFolder, int accountCount)
        {
            AvailableFolders = availableFolders;
            AccountCount = accountCount;
            SelectedFolder = currentFolder;

            ConfirmCommand = new RelayCommand(_ =>
            {
                if (!string.IsNullOrEmpty(SelectedFolder))
                {
                    DialogResult = true;
                    RequestClose?.Invoke();
                }
            });

            CancelCommand = new RelayCommand(_ =>
            {
                DialogResult = false;
                RequestClose?.Invoke();
            });
        }
    }
}
