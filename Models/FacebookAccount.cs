using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace FPlusClone.Models
{
    public class FacebookAccount : INotifyPropertyChanged
    {
        private bool _isSelected;
        public bool IsSelected
        {
            get => _isSelected;
            set
            {
                if (_isSelected != value)
                {
                    _isSelected = value;
                    OnPropertyChanged();
                }
            }
        }

        /// <summary>
        /// Set IsSelected trực tiếp mà KHÔNG raise PropertyChanged.
        /// Dùng cho bulk select/deselect để tránh N lần re-render UI.
        /// Gọi ItemsView.Refresh() sau khi xong.
        /// </summary>
        public void SetSelectedSilently(bool value)
        {
            _isSelected = value;
        }


        private int _index;
        public int Index { get => _index; set { if (_index != value) { _index = value; OnPropertyChanged(); } } }

        private string _userName;
        public string UserName { get => _userName; set { if (_userName != value) { _userName = value; OnPropertyChanged(); } } }

        private string _password;
        public string Password { get => _password; set { if (_password != value) { _password = value; OnPropertyChanged(); } } }

        private string _uid;
        public string Uid { get => _uid; set { if (_uid != value) { _uid = value; OnPropertyChanged(); } } }

        private string _name;
        public string Name { get => _name; set { if (_name != value) { _name = value; OnPropertyChanged(); } } }

        private string _birthday;
        public string Birthday { get => _birthday; set { if (_birthday != value) { _birthday = value; OnPropertyChanged(); } } }

        private string _gender;
        public string Gender { get => _gender; set { if (_gender != value) { _gender = value; OnPropertyChanged(); } } }

        private int _friends;
        public int Friends { get => _friends; set { if (_friends != value) { _friends = value; OnPropertyChanged(); } } }

        private int _groups;
        public int Groups { get => _groups; set { if (_groups != value) { _groups = value; OnPropertyChanged(); } } }

        private string _cookie;
        public string Cookie { get => _cookie; set { if (_cookie != value) { _cookie = value; OnPropertyChanged(); } } }

        private string _token;
        public string Token { get => _token; set { if (_token != value) { _token = value; OnPropertyChanged(); } } }

        private string _email;
        public string Email { get => _email; set { if (_email != value) { _email = value; OnPropertyChanged(); } } }

        private string _passEmail;
        public string PassEmail { get => _passEmail; set { if (_passEmail != value) { _passEmail = value; OnPropertyChanged(); } } }

        private string _twoFA;
        public string TwoFA { get => _twoFA; set { if (_twoFA != value) { _twoFA = value; OnPropertyChanged(); } } }

        private string _proxy;
        public string Proxy { get => _proxy; set { if (_proxy != value) { _proxy = value; OnPropertyChanged(); } } }

        private string _userAgent;
        public string UserAgent { get => _userAgent; set { if (_userAgent != value) { _userAgent = value; OnPropertyChanged(); } } }

        private string _status;
        public string Status { get => _status; set { if (_status != value) { _status = value; OnPropertyChanged(); } } }

        private string _folder;
        public string Folder { get => _folder; set { if (_folder != value) { _folder = value; OnPropertyChanged(); } } }

        private string _note;
        public string Note { get => _note; set { if (_note != value) { _note = value; OnPropertyChanged(); } } }



        public event PropertyChangedEventHandler PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
