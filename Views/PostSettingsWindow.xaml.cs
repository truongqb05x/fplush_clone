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
            // TODO: Save logic to ViewModels / Settings model here
            MessageBox.Show("Đã lưu cấu hình đăng bài!", "Thông báo", MessageBoxButton.OK, MessageBoxImage.Information);
            this.DialogResult = true;
            this.Close();
        }
    }
}
