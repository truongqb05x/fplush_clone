using FPlusClone.Models;
using System.Windows.Input;

namespace FPlusClone.ViewModels
{
    public class TabSpamGroupViewModel : BaseTabViewModel
    {
        private string _groupUids;
        public string GroupUids
        {
            get => _groupUids;
            set { if (_groupUids != value) { _groupUids = value; OnPropertyChanged(); } }
        }

        private string _comments;
        public string Comments
        {
            get => _comments;
            set { if (_comments != value) { _comments = value; OnPropertyChanged(); } }
        }

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

        public ICommand StartTaskCommand { get; }
        public ICommand StopTaskCommand { get; }

        public TabSpamGroupViewModel()
        {
            StartTaskCommand = new RelayCommand(_ => StartTask());
            StopTaskCommand = new RelayCommand(_ => StopTask());
        }

        private void StartTask()
        {
            System.Windows.MessageBox.Show("Bắt đầu chạy tiến trình...");
            // Logic calling Python will be implemented later
        }

        private void StopTask()
        {
            System.Windows.MessageBox.Show("Đã yêu cầu dừng tiến trình.");
        }
    }
}
