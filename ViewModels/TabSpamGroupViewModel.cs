using FPlusClone.Models;
using System.Windows.Input;
using System.Linq;

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

        private bool _isSequentialComment = true;
        public bool IsSequentialComment
        {
            get => _isSequentialComment;
            set { if (_isSequentialComment != value) { _isSequentialComment = value; OnPropertyChanged(); } }
        }

        private bool _isRandomComment;
        public bool IsRandomComment
        {
            get => _isRandomComment;
            set { if (_isRandomComment != value) { _isRandomComment = value; OnPropertyChanged(); } }
        }

        private bool _isTextComment = true;
        public bool IsTextComment
        {
            get => _isTextComment;
            set { if (_isTextComment != value) { _isTextComment = value; OnPropertyChanged(); } }
        }

        private bool _isImageComment;
        public bool IsImageComment
        {
            get => _isImageComment;
            set { if (_isImageComment != value) { _isImageComment = value; OnPropertyChanged(); } }
        }

        private string _imageFolderPath;
        public string ImageFolderPath
        {
            get => _imageFolderPath;
            set { if (_imageFolderPath != value) { _imageFolderPath = value; OnPropertyChanged(); } }
        }

        public System.Collections.ObjectModel.ObservableCollection<CommentModel> CommentsList { get; set; } = new System.Collections.ObjectModel.ObservableCollection<CommentModel>();

        private string _newComment;
        public string NewComment
        {
            get => _newComment;
            set { if (_newComment != value) { _newComment = value; OnPropertyChanged(); } }
        }

        public ICommand AddCommentCommand { get; }
        public ICommand EditCommentCommand { get; }
        public ICommand DeleteCommentCommand { get; }

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

        private bool _isCheckApproval;
        public bool IsCheckApproval
        {
            get => _isCheckApproval;
            set { if (_isCheckApproval != value) { _isCheckApproval = value; OnPropertyChanged(); } }
        }

        public ICommand StartTaskCommand { get; }
        public ICommand StopTaskCommand { get; }
        public ICommand SelectImageFolderCommand { get; }

        private readonly string commentsFilePath = "comments_spamgroup.txt";

        public TabSpamGroupViewModel()
        {
            LoadComments();

            SelectImageFolderCommand = new RelayCommand(_ =>
            {
                var dialog = new Microsoft.Win32.OpenFolderDialog
                {
                    Title = "Chọn thư mục chứa ảnh bình luận"
                };

                if (dialog.ShowDialog() == true)
                {
                    ImageFolderPath = dialog.FolderName;
                }
            });

            StartTaskCommand = new RelayCommand(_ => StartTask());
            StopTaskCommand = new RelayCommand(_ => StopTask());

            AddCommentCommand = new RelayCommand(_ =>
            {
                if (!string.IsNullOrWhiteSpace(NewComment))
                {
                    CommentsList.Add(new CommentModel { Index = CommentsList.Count + 1, Content = NewComment });
                    SaveComments();
                    NewComment = string.Empty;
                }
            });

            DeleteCommentCommand = new RelayCommand(obj =>
            {
                if (obj is CommentModel comment)
                {
                    CommentsList.Remove(comment);
                    for (int i = 0; i < CommentsList.Count; i++)
                    {
                        CommentsList[i].Index = i + 1;
                    }
                    SaveComments();
                }
            });

            EditCommentCommand = new RelayCommand(obj =>
            {
                if (obj is CommentModel oldComment)
                {
                    var window = new Views.EditCommentWindow(oldComment.Content)
                    {
                        Owner = System.Windows.Application.Current.MainWindow
                    };

                    if (window.ShowDialog() == true)
                    {
                        string newText = window.CommentText;
                        if (!string.IsNullOrWhiteSpace(newText) && newText != oldComment.Content)
                        {
                            oldComment.Content = newText;
                            SaveComments();
                        }
                    }
                }
            });
        }

        private void LoadComments()
        {
            if (System.IO.File.Exists(commentsFilePath))
            {
                var lines = System.IO.File.ReadAllLines(commentsFilePath);
                int index = 1;
                foreach (var line in lines)
                {
                    if (!string.IsNullOrWhiteSpace(line))
                    {
                        CommentsList.Add(new CommentModel { Index = index++, Content = line });
                    }
                }
            }
        }

        private void SaveComments()
        {
            var lines = CommentsList.Select(c => c.Content).ToArray();
            System.IO.File.WriteAllLines(commentsFilePath, lines);
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
