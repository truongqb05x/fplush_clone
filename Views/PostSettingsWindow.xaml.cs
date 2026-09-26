using System.Windows;
using Microsoft.Win32;

namespace FPlusClone.Views
{
    public partial class PostSettingsWindow : Window
    {
        public PostSettingsWindow()
        {
            InitializeComponent();
        }

        private void BtnBrowseImage_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog openFileDialog = new OpenFileDialog();
            openFileDialog.Filter = "Image files (*.jpg, *.jpeg, *.png) | *.jpg; *.jpeg; *.png";
            if (openFileDialog.ShowDialog() == true)
            {
                TxtImagePath.Text = openFileDialog.FileName;
            }
        }

        private void BtnBrowseContent_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog openFileDialog = new OpenFileDialog();
            openFileDialog.Filter = "Text files (*.txt)|*.txt";
            if (openFileDialog.ShowDialog() == true)
            {
                TxtContentPath.Text = openFileDialog.FileName;
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            this.DialogResult = false;
            this.Close();
        }

        private void BtnSave_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                int mode = RbManual.IsChecked == true ? 1 : 2;
                var config = new
                {
                    Mode = mode,
                    ImagePath = TxtImagePath.Text,
                    ContentPath = TxtContentPath.Text,
                    IsTagFriends = ChkTagFriends.IsChecked == true,
                    IsCheckIn = ChkCheckIn.IsChecked == true,
                    IsFeeling = ChkFeeling.IsChecked == true
                };

                string json = System.Text.Json.JsonSerializer.Serialize(config);
                string path = System.IO.Path.Combine(System.AppDomain.CurrentDomain.BaseDirectory, "post_config.json");
                // If running from bin folder, go to root (or let it save in bin)
                if (path.Contains("bin"))
                {
                    path = System.IO.Path.Combine(System.IO.Path.GetFullPath(System.IO.Path.Combine(System.AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..")), "post_config.json");
                }
                
                System.IO.File.WriteAllText(path, json);
                MessageBox.Show("Đã lưu cấu hình đăng bài!", "Thông báo", MessageBoxButton.OK, MessageBoxImage.Information);
                this.DialogResult = true;
                this.Close();
            }
            catch (System.Exception ex)
            {
                MessageBox.Show("Lỗi khi lưu cấu hình: " + ex.Message, "Lỗi", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }
}
