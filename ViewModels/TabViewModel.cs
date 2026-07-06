namespace FPlusClone.ViewModels
{
    public class TabViewModel : ViewModelBase
    {
        private string _header;
        public string Header
        {
            get => _header;
            set => SetProperty(ref _header, value);
        }

        private bool _isSelected;
        public bool IsSelected
        {
            get => _isSelected;
            set => SetProperty(ref _isSelected, value);
        }

        // You can add ContentViewModel here if each tab has unique logic
    }
}
