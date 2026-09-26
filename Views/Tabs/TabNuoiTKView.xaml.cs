using System.Windows;
using System.Windows.Controls;
using FPlusClone.ViewModels;

namespace FPlusClone.Views.Tabs
{
    public partial class TabNuoiTKView : UserControl 
    { 
        public TabNuoiTKView() { InitializeComponent(); } 

        private void BtnStop_Click(object sender, RoutedEventArgs e)
        {
            if (MessageBox.Show("Bạn có chắc chắn muốn dừng tiến trình?", "Xác nhận", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
            {
                if (DataContext is TabNuoiTKViewModel vm && vm.StopTaskCommand.CanExecute(null))
                {
                    vm.StopTaskCommand.Execute(null);
                    MessageBox.Show("Đã dừng tiến trình thành công!", "Thông báo", MessageBoxButton.OK, MessageBoxImage.Information);
                }
            }
        }

        private void BtnPostSettings_Click(object sender, RoutedEventArgs e)
        {
            var settingsWindow = new PostSettingsWindow();
            settingsWindow.ShowDialog();
        }
    }
}
