from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt, QTimer

from license_plate_monitor.ui.threads import VideoThread, YoutubeInfoThread
from license_plate_monitor.ui.widgets import AISettingTab, DetectionCard, SourceTab

if TYPE_CHECKING:
    from license_plate_monitor.ai.detector import LicensePlateDetector
from PyQt6.QtGui import QCloseEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("License Plate Monitor System")
        self.resize(1300, 800)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.video_thread: VideoThread | None = None
        self.stored_detector: LicensePlateDetector | None = None

        self.tabs = QTabWidget()
        self.source_tab = SourceTab()
        self.ai_tab = AISettingTab()

        self.tabs.addTab(self.source_tab, "📡 Nguồn Video")
        self.tabs.addTab(self.ai_tab, "🤖 Cấu hình AI")

        self.action_group = QGroupBox("Thao tác nhanh")
        action_layout = QHBoxLayout(self.action_group)

        # Nút Start/Stop
        self.start_btn = QPushButton("Bắt đầu")
        self.start_btn.clicked.connect(self.toggle_detection)
        self.start_btn.setStyleSheet(
            "background-color: #2e7d32; color: white; font-weight: bold;"
        )

        # Nút Tạm dừng
        self.pause_btn = QPushButton("Tạm dừng")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)

        # Clear History Button
        self.clear_sidebar_btn = QPushButton("Xóa lịch sử")
        self.clear_sidebar_btn.setStyleSheet("background-color: #444; color: white;")
        self.clear_sidebar_btn.setEnabled(False)
        self.clear_sidebar_btn.clicked.connect(self.clear_sidebar)

        action_layout.addWidget(self.start_btn)
        action_layout.addWidget(self.pause_btn)
        action_layout.addWidget(self.clear_sidebar_btn)

        # Layout chính
        main_vbox = QVBoxLayout()

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #E0E0E0;
                height: 10px;
                border-radius: 5px;
                text-align: center;
                color: black;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background-color: #3498db;
            }
            """
        )
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()

        # Notification Area
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng.")
        self.status_bar.setStyleSheet("font-size: 14px;")

        # Dashboard Bar
        self.stats_widget = QWidget()
        self.stats_widget.setStyleSheet(
            "background-color: #252525; border-bottom: 1px solid #444;"
        )
        self.stats_layout = QHBoxLayout(self.stats_widget)
        self.stats_label = QLabel("📊 THỐNG KÊ: Đang chờ dữ liệu...")
        self.stats_label.setStyleSheet(
            "color: #00FF00; font-weight: bold; font-size: 16px;"
        )
        self.stats_layout.addWidget(self.stats_label)

        self.source_tab.combo.currentTextChanged.connect(self.on_source_type_changed)
        self.source_tab.input.textChanged.connect(self.on_url_changed)

        # Ngang (Video | Sidebar)
        content_layout = QHBoxLayout()

        # Video Area
        self.video_label = QLabel("Đang chờ bắt đầu...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.video_label, stretch=4)  # Chiếm 4 phần diện tích

        # Sidebar Area
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_container = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFixedWidth(300)
        self.sidebar_scroll.setWidget(self.sidebar_container)
        content_layout.addWidget(self.sidebar_scroll, stretch=1)

        # Thêm vào main layout
        main_vbox.addWidget(self.stats_widget)
        main_vbox.addWidget(self.tabs)
        main_vbox.addWidget(self.action_group)
        main_vbox.addWidget(self.progress_bar)
        main_vbox.addLayout(content_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_vbox)
        self.setCentralWidget(central_widget)

    def update_stats(self, counts: dict[str, int]) -> None:
        """Cập nhật dòng chữ thống kê trên Dashboard"""
        stat_items = [f"{label.upper()}: {value}" for label, value in counts.items()]
        display_text = "  |  ".join(stat_items)
        self.stats_label.setText(f"📊 THỐNG KÊ: {display_text}")

    def update_video(self, qt_image: QImage) -> None:
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def add_detection_card(self, data: dict[str, Any]) -> None:
        # Giới hạn số lượng card trên màn hình để tránh crash
        max_cards = 20
        while self.sidebar_layout.count() >= max_cards:
            item = self.sidebar_layout.takeAt(self.sidebar_layout.count() - 1)
            if item:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        # Thêm card mới lên trên cùng của sidebar
        card = DetectionCard(data)
        self.sidebar_layout.insertWidget(0, card)
        # Hiệu ứng cuộn nhẹ nhàng về đầu danh sách
        scrollbar = self.sidebar_scroll.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(0)

    def clear_sidebar(self) -> None:
        """Xóa sạch các card trong sidebar"""
        while self.sidebar_layout.count() > 0:
            item = self.sidebar_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self.status_bar.showMessage("Đã xóa lịch sử nhận diện.")

    def on_source_type_changed(self, text: str) -> None:
        """Tự động ẩn/hiện độ phân giải tùy theo nguồn"""
        is_youtube = text.lower() == "youtube"
        self.source_tab.combo.setEnabled(is_youtube)

    def toggle_detection(self) -> None:
        """Xử lý sự kiện nhấn nút Bắt đầu / Dừng hẳn"""
        # Nếu đang chạy thì dừng lại
        if self.video_thread and self.video_thread.isRunning():
            # Ngăn frame nào lọt vào sau khi xóa
            self.video_thread.change_pixmap_signal.disconnect()
            self.video_thread.stop()
            self.video_thread.deleteLater()  # Xoá vùng nhớ của thread cũ ngay lập tức
            self.video_thread = None  # Set None tránh trỏ đến vùng nhớ không tồn tại

            self.video_label.clear()
            self.video_label.setText("⏹️ HỆ THỐNG ĐÃ DỪNG")
            self.video_label.setStyleSheet(
                "color: #FF5555; font-weight: bold; font-size: 18px;"
            )

            # Clear sidebar
            while self.sidebar_layout.count() > 0:
                item = self.sidebar_layout.takeAt(0)
                if item:
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()

            self.start_btn.setText("Bắt đầu")
            self.start_btn.setStyleSheet("background-color: #2e7d32; color: white;")

            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("Tạm dừng")

            self.status_bar.showMessage("Đã dừng hệ thống và dọn dẹp sidebar.")
        else:
            # Nếu đang dừng thì bắt đầu luồng mới
            source = self.source_tab.input.text()
            source_type = self.source_tab.combo.currentText()
            res = self.source_tab.res_combo.currentText()

            if not source and source_type.lower() != "webcam":
                return  # Cần có link hoặc đường dẫn

            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.stats_label.setText("📊 THỐNG KÊ: Đang khởi tạo...")

            conf_threshold = self.ai_tab.conf_spin.value()
            show_labels = self.ai_tab.show_labels.isChecked()
            show_boxes = self.ai_tab.show_boxes.isChecked()
            auto_save = self.ai_tab.auto_save.isChecked()

            self.video_thread = VideoThread(
                source,
                source_type,
                res,
                self.stored_detector,
                conf_threshold,
                show_labels,
                show_boxes,
                auto_save,
            )

            self.video_thread.progress_signal.connect(self.update_notification)
            self.video_thread.detector_ready_signal.connect(self.save_detector)
            self.video_thread.change_pixmap_signal.connect(self.update_video)
            self.video_thread.new_detection_signal.connect(self.add_detection_card)
            self.video_thread.stats_signal.connect(self.update_stats)
            self.video_thread.start()

            self.start_btn.setText("Dừng hẳn")
            self.start_btn.setStyleSheet("background-color: #c62828; color: white;")
            self.pause_btn.setEnabled(True)
            self.status_bar.showMessage("Đang chuẩn bị luồng dữ liệu...")

    def toggle_pause(self) -> None:
        """Xử lý sự kiện nhấn nút Tạm dừng / Tiếp tục"""
        if self.video_thread is None:
            return

        if self.video_thread._is_paused:
            self.video_thread.resume()
            self.pause_btn.setText("Tạm dừng")
            self.status_bar.showMessage("Đang tiếp tục nhận diện...")
        else:
            self.video_thread.pause()
            self.pause_btn.setText("Tiếp tục")
            self.status_bar.showMessage("Đang tạm dừng.")

    def update_notification(
        self, message: str, value: int, wait_time_ms: int = 3000
    ) -> None:
        """Cập nhật thanh tiến trình và thông báo cho người dùng"""
        self.status_bar.showMessage(message)
        self.progress_bar.setValue(value)
        if value >= 100:
            # Tự động ẩn progress bar sau n giây khi hoàn thành
            QTimer.singleShot(wait_time_ms, self.progress_bar.hide)

    def save_detector(self, detector_obj: LicensePlateDetector) -> None:
        """Lưu trữ detector vào MainWindow để dùng lại"""
        self.stored_detector = detector_obj
        print("[+] Đã lưu trữ Model vào bộ nhớ hệ thống.")

    def on_url_changed(self, text: str) -> None:
        """Kiểm tra nếu là link YouTube thì tự động lấy độ phân giải"""
        source_type = self.source_tab.combo.currentText().lower()
        # Chỉ tự động lấy thông tin nếu đang chọn nguồn là YouTube và link có vẻ hợp lệ
        if source_type == "youtube":
            if "youtube.com" in text or "youtu.be" in text:
                self.source_tab.res_combo.clear()
                self.source_tab.res_combo.addItem("Đang lấy danh sách...")
                self.source_tab.res_combo.setEnabled(False)

                # Khởi chạy luồng lấy thông tin ngầm
                self.info_thread = YoutubeInfoThread(text)
                self.info_thread.resolutions_signal.connect(self.update_resolution_list)
                self.info_thread.error_signal.connect(self.on_info_error)
                self.info_thread.start()
            else:
                self.source_tab.res_combo.clear()
                self.source_tab.res_combo.setEnabled(False)

    def update_resolution_list(self, resolutions: list[str]) -> None:
        """Cập nhật danh sách độ phân giải thực tế vào ComboBox"""
        self.source_tab.res_combo.clear()
        resolutions.reverse()
        self.source_tab.res_combo.addItems(resolutions)
        self.source_tab.res_combo.setEnabled(True)
        # Tự động chọn độ phân giải cao nhất có sẵn
        if resolutions:
            self.source_tab.res_combo.setCurrentIndex(0)

    def on_info_error(self, error_msg: str) -> None:
        """Xử lý khi không lấy được thông tin video"""
        self.source_tab.res_combo.clear()
        self.source_tab.res_combo.addItem("Lỗi lấy thông tin")
        self.source_tab.res_combo.setEnabled(False)
        print(f"[!] Lỗi lấy thông tin YouTube: {error_msg}")

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Dừng luồng AI, Giải phóng Camera, Chấp nhận đóng, Tự động gọi"""
        if self.video_thread is not None:
            self.video_thread.stop()
        if event:
            event.accept()
