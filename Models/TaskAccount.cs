using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace FPlusClone.Models
{
    public class TaskAccount : INotifyPropertyChanged
    {
        private FacebookAccount _account;
        public FacebookAccount Account
        {
            get => _account;
            set { if (_account != value) { _account = value; OnPropertyChanged(); } }
        }

        private bool _isSelected;
        public bool IsSelected
        {
            get => _isSelected;
            set { if (_isSelected != value) { _isSelected = value; OnPropertyChanged(); } }
        }

        private string _status = "Chờ chạy";
        public string Status
        {
            get => _status;
            set { if (_status != value) { _status = value; OnPropertyChanged(); } }
        }

        private string _progress = "0/1";
        public string Progress
        {
            get => _progress;
            set { if (_progress != value) { _progress = value; OnPropertyChanged(); } }
        }

        private string _proxy = "Direct";
        public string Proxy
        {
            get => _proxy;
            set { if (_proxy != value) { _proxy = value; OnPropertyChanged(); } }
        }

        public event PropertyChangedEventHandler PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
