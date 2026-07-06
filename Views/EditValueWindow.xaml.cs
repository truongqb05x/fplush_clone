using System;
using System.Windows;
using System.Windows.Input;
using FPlusClone.ViewModels;

namespace FPlusClone.Views
{
    public partial class EditValueWindow : Window
    {
        public EditValueWindow()
        {
            InitializeComponent();
        }
    }

    public class EditValueViewModel : ViewModelBase
    {
        private string _title;
        public string Title { get => _title; set => SetProperty(ref _title, value); }

        private string _prompt;
        public string Prompt { get => _prompt; set => SetProperty(ref _prompt, value); }

        private string _value;
        public string Value { get => _value; set => SetProperty(ref _value, value); }

        public ICommand SaveCommand { get; }
        public ICommand CloseCommand { get; }

        public bool? DialogResult { get; private set; }

        public event Action RequestClose;

        public EditValueViewModel(string title, string prompt, string initialValue)
        {
            Title = title;
            Prompt = prompt;
            Value = initialValue;

            SaveCommand = new RelayCommand(_ => {
                DialogResult = true;
                RequestClose?.Invoke();
            });

            CloseCommand = new RelayCommand(_ => {
                DialogResult = false;
                RequestClose?.Invoke();
            });
        }
    }
}
