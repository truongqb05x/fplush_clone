using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace FPlusClone.ViewModels
{
    public class MappingOption : ViewModelBase
    {
        private string _selectedValue;
        public string SelectedValue
        {
            get => _selectedValue;
            set => SetProperty(ref _selectedValue, value);
        }
    }
}
