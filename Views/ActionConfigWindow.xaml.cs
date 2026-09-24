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
                IsChatWithEachOther = config.IsChatWithEachOther
            };

            DataContext = Config;
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
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
