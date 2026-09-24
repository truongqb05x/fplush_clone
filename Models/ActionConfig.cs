using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace FPlusClone.Models
{
    public class ActionConfig : INotifyPropertyChanged
    {
        private bool _isScrollFeed;
        public bool IsScrollFeed { get => _isScrollFeed; set { if (_isScrollFeed != value) { _isScrollFeed = value; OnPropertyChanged(); } } }

        private int _scrollTimeMin = 10;
        public int ScrollTimeMin { get => _scrollTimeMin; set { if (_scrollTimeMin != value) { _scrollTimeMin = value; OnPropertyChanged(); } } }

        private int _scrollTimeMax = 30;
        public int ScrollTimeMax { get => _scrollTimeMax; set { if (_scrollTimeMax != value) { _scrollTimeMax = value; OnPropertyChanged(); } } }

        private bool _isReadNotifications;
        public bool IsReadNotifications { get => _isReadNotifications; set { if (_isReadNotifications != value) { _isReadNotifications = value; OnPropertyChanged(); } } }

        private int _readNotificationsCount = 5;
        public int ReadNotificationsCount { get => _readNotificationsCount; set { if (_readNotificationsCount != value) { _readNotificationsCount = value; OnPropertyChanged(); } } }

        private bool _isAddFriends;
        public bool IsAddFriends { get => _isAddFriends; set { if (_isAddFriends != value) { _isAddFriends = value; OnPropertyChanged(); } } }

        private int _addFriendsCount = 5;
        public int AddFriendsCount { get => _addFriendsCount; set { if (_addFriendsCount != value) { _addFriendsCount = value; OnPropertyChanged(); } } }

        private bool _isRandomAction;
        public bool IsRandomAction { get => _isRandomAction; set { if (_isRandomAction != value) { _isRandomAction = value; OnPropertyChanged(); } } }

        private bool _isChatWithEachOther;
        public bool IsChatWithEachOther { get => _isChatWithEachOther; set { if (_isChatWithEachOther != value) { _isChatWithEachOther = value; OnPropertyChanged(); } } }

        // Mới thêm cho cảm xúc
        private bool _isLikePost;
        public bool IsLikePost { get => _isLikePost; set { if (_isLikePost != value) { _isLikePost = value; OnPropertyChanged(); } } }

        private bool _isReactionLike = true;
        public bool IsReactionLike { get => _isReactionLike; set { if (_isReactionLike != value) { _isReactionLike = value; OnPropertyChanged(); } } }

        private bool _isReactionLove;
        public bool IsReactionLove { get => _isReactionLove; set { if (_isReactionLove != value) { _isReactionLove = value; OnPropertyChanged(); } } }

        private bool _isReactionCare;
        public bool IsReactionCare { get => _isReactionCare; set { if (_isReactionCare != value) { _isReactionCare = value; OnPropertyChanged(); } } }

        private bool _isReactionHaha;
        public bool IsReactionHaha { get => _isReactionHaha; set { if (_isReactionHaha != value) { _isReactionHaha = value; OnPropertyChanged(); } } }

        private bool _isReactionWow;
        public bool IsReactionWow { get => _isReactionWow; set { if (_isReactionWow != value) { _isReactionWow = value; OnPropertyChanged(); } } }

        private bool _isReactionSad;
        public bool IsReactionSad { get => _isReactionSad; set { if (_isReactionSad != value) { _isReactionSad = value; OnPropertyChanged(); } } }

        private bool _isReactionAngry;
        public bool IsReactionAngry { get => _isReactionAngry; set { if (_isReactionAngry != value) { _isReactionAngry = value; OnPropertyChanged(); } } }

        private int _reactionDelayMin = 5;
        public int ReactionDelayMin { get => _reactionDelayMin; set { if (_reactionDelayMin != value) { _reactionDelayMin = value; OnPropertyChanged(); } } }

        private int _reactionDelayMax = 15;
        public int ReactionDelayMax { get => _reactionDelayMax; set { if (_reactionDelayMax != value) { _reactionDelayMax = value; OnPropertyChanged(); } } }


        public event PropertyChangedEventHandler PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
