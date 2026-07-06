using System.Windows;
using FPlusClone.ViewModels;

namespace FPlusClone.Views
{
    public partial class ImportAccountWindow : Window
    {
        public ImportAccountWindow()
        {
            InitializeComponent();
        }

        public ImportAccountWindow(ImportAccountViewModel viewModel) : this()
        {
            DataContext = viewModel;
            viewModel.RequestClose += Close;
        }
    }
}
