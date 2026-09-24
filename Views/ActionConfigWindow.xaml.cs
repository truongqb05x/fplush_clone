using FPlusClone.Models;
using System.Windows;

namespace FPlusClone.Views
{
    public partial class ActionConfigWindow : Window
    {
        public ActionConfig Config { get; set; }

        public ActionConfigWindow(ActionConfig config)
        {
            InitializeComponent();
            
            // Create a clone to allow cancel
            Config = new ActionConfig
            {
                IsScrollFeed = config.IsScrollFeed,
                ScrollTimeMin = config.ScrollTimeMin,
                ScrollTimeMax = config.ScrollTimeMax,
                IsReadNotifications = config.IsReadNotifications,
                ReadNotificationsCount = config.ReadNotificationsCount,
                IsAddFriends = config.IsAddFriends,
                AddFriendsCount = config.AddFriendsCount,
                IsRandomAction = config.IsRandomAction,
                IsChatWithEachOther = config.IsChatWithEachOther,
                IsLikePost = config.IsLikePost,
                IsReactionLike = config.IsReactionLike,
                IsReactionLove = config.IsReactionLove,
                IsReactionCare = config.IsReactionCare,
                IsReactionHaha = config.IsReactionHaha,
                IsReactionWow = config.IsReactionWow,
                IsReactionSad = config.IsReactionSad,
                IsReactionAngry = config.IsReactionAngry,
                ReactionDelayMin = config.ReactionDelayMin,
                ReactionDelayMax = config.ReactionDelayMax
            };

            DataContext = Config;
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            if (Config.IsLikePost)
            {
                if (Config.ReactionDelayMax > Config.ScrollTimeMax)
                {
                    MessageBox.Show("Thời gian delay của react không được lớn hơn thời gian lướt bài (ScrollTimeMax)!", "Lỗi hợp logic", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
                if (Config.ReactionDelayMin > Config.ReactionDelayMax)
                {
                    MessageBox.Show("Thời gian delay min không được lớn hơn delay max!", "Lỗi", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
            }

            DialogResult = true;
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
