using System.Windows;
using FPlusClone.ViewModels;

namespace FPlusClone.Views
{
    public partial class CopyCustomWindow : Window
    {
        public CopyCustomWindow(CopyCustomViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
            viewModel.RequestClose += () => this.Close();
        }

        private void Refresh_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is CopyCustomViewModel vm)
            {
                vm.UpdatePreview();
            }
        }
    }
}
