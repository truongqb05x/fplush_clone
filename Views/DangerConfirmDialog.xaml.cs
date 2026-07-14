using System.Windows;

namespace FPlusClone.Views
{
    public partial class DangerConfirmDialog : Window
    {
        public bool Confirmed { get; private set; } = false;

        public DangerConfirmDialog(string message, Window owner = null)
        {
            InitializeComponent();
            WarningMessage.Text = message;
            if (owner != null) Owner = owner;
        }

        private void Confirm_Click(object sender, RoutedEventArgs e)
        {
            Confirmed = true;
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            Confirmed = false;
            Close();
        }
    }
}
