using System.Windows;

namespace FPlusClone.Views
{
    public partial class EditCommentWindow : Window
    {
        public string CommentText { get; private set; }

        public EditCommentWindow(string initialText)
        {
            InitializeComponent();
            txtComment.Text = initialText;
            txtComment.SelectAll();
            txtComment.Focus();
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            CommentText = txtComment.Text;
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
