using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Input;
using FPlusClone.Models;

namespace FPlusClone.ViewModels
{
    public class CopyCustomViewModel : ViewModelBase
    {
        private readonly List<FacebookAccount> _sourceAccounts;

        public ObservableCollection<string> ColumnOptions { get; }
        public ObservableCollection<MappingOption> SelectedMappings { get; }


        private string _previewText;
        public string PreviewText
        {
            get => _previewText;
            set => SetProperty(ref _previewText, value);
        }

        public ICommand CopyCommand { get; }
        public ICommand CloseCommand { get; }

        public event Action RequestClose;

        public CopyCustomViewModel(IEnumerable<FacebookAccount> selectedAccounts)
        {
            _sourceAccounts = selectedAccounts?.ToList() ?? new List<FacebookAccount>();

            ColumnOptions = new ObservableCollection<string>
            {
                "None", "UID", "Pass", "Cookie", "Token", "Email", "PassEmail", "2FA", "Proxy", "UserAgent", "Name", "Birthday", "Note"
            };

            SelectedMappings = new ObservableCollection<MappingOption>();
            
            var initialValues = new[] { "UID", "Pass", "Cookie", "Token", "None", "None", "None", "None", "None", "None" };
            foreach (var val in initialValues)
            {
                var opt = new MappingOption { SelectedValue = val };
                opt.PropertyChanged += (s, e) => UpdatePreview();
                SelectedMappings.Add(opt);
            }

            CopyCommand = new RelayCommand(_ => ExecuteCopy());
            CloseCommand = new RelayCommand(_ => RequestClose?.Invoke());

            UpdatePreview();
        }

        public void UpdatePreview()
        {
            if (_sourceAccounts.Count == 0)
            {
                PreviewText = "No accounts selected.";
                return;
            }

            PreviewText = FormatAccount(_sourceAccounts[0]);
        }

        private string FormatAccount(FacebookAccount acc)
        {
            var parts = new List<string>();
            foreach (var mappingOpt in SelectedMappings)
            {
                string mapping = mappingOpt.SelectedValue;
                if (string.IsNullOrEmpty(mapping) || mapping == "None") continue;

                string val = "";
                switch (mapping)
                {
                    case "UID": val = acc.Uid; break;
                    case "Pass": val = acc.Password; break;
                    case "Cookie": val = acc.Cookie; break;
                    case "Token": val = acc.Token; break;
                    case "Email": val = acc.Email; break;
                    case "PassEmail": val = acc.PassEmail; break;
                    case "2FA": val = acc.TwoFA; break;
                    case "Proxy": val = acc.Proxy; break;
                    case "UserAgent": val = acc.UserAgent; break;
                    case "Name": val = acc.Name; break;
                    case "Birthday": val = acc.Birthday; break;
                    case "Note": val = acc.Note; break;
                }
                parts.Add(val ?? "");
            }
            return string.Join("|", parts);
        }

        private void ExecuteCopy()
        {
            if (_sourceAccounts.Count == 0) return;

            var sb = new StringBuilder();
            foreach (var acc in _sourceAccounts)
            {
                sb.AppendLine(FormatAccount(acc));
            }

            Clipboard.SetText(sb.ToString().Trim());
            RequestClose?.Invoke();
        }
    }
}

