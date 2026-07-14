using System;
using System.Globalization;
using System.Windows.Data;

namespace FPlusClone.Views
{
    /// <summary>
    /// Chuyển AlternationIndex (0-based) → số thứ tự hiển thị (1-based).
    /// Dùng cho cột # trong DataGrid, tự động cập nhật theo view hiện tại
    /// mà không cần lưu Index vào model.
    /// </summary>
    public class RowNumberConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
            => value is int index ? index + 1 : value;

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
            => throw new NotImplementedException();
    }
}
