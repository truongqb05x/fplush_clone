using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace FPlusClone.Models
{
    public class CommentModel : INotifyPropertyChanged
    {
        private int _index;
        public int Index { get => _index; set { _index = value; OnPropertyChanged(); } }

        private string _content;
        public string Content { get => _content; set { _content = value; OnPropertyChanged(); } }

        public event PropertyChangedEventHandler PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
