import logging
import sys
import traceback
from types import TracebackType

from PyQt6.QtWidgets import QApplication

from license_plate_monitor.ui.gui_app import MainWindow



# Hàm này sẽ bắt mọi lỗi chưa được xử lý và in ra terminal
def excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    print("=== ĐÃ XẢY RA LỖI HỆ THỐNG ===")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    sys.exit(1)


sys.excepthook = excepthook


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Khởi tạo ứng dụng PyQt6
    app = QApplication(sys.argv)

    # Khởi tạo cửa sổ chính
    window = MainWindow()
    window.show()

    # Chạy vòng lặp sự kiện của ứng dụng
    # sys.exit đảm bảo chương trình kết thúc sạch sẽ khi đóng cửa sổ
    sys.exit(app.exec())
