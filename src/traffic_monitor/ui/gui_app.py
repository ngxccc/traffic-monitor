from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt, QTimer

from traffic_monitor.ui.threads import VideoThread, YoutubeInfoThread
from traffic_monitor.ui.widgets import DetectionCard

if TYPE_CHECKING:
    from traffic_monitor.ai.detector import TrafficDetector
from PyQt6.QtGui import QCloseEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hệ thống giám sát Giao thông")
        self.resize(1300, 800)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.video_thread: VideoThread | None = None
        self.stored_detector: TrafficDetector | None = None

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
        self.progress_bar.setValue(50)
        self.progress_bar.show()

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

        # Control Panel
        self.control_group = QGroupBox("Cấu hình nguồn vào")
        control_layout = QHBoxLayout(self.control_group)

        # Chọn loại nguồn
        self.source_combo = QComboBox()
        self.source_combo.addItems(
            ["YouTube", "Webcam", "Local File | Link MP4", "RTSP camera"]
        )
        self.source_combo.currentTextChanged.connect(self.on_source_type_changed)

        # Nhập đường dẫn/URL
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Nhập URL YouTube hoặc đường dẫn file...")
        self.source_input.textChanged.connect(self.on_url_changed)

        # Chọn độ phân giải (chỉ hiện cho YouTube)
        self.res_combo = QComboBox()
        self.res_combo.setEnabled(False)
        self.res_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

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

        # Thêm vào Control Panel
        control_layout.addWidget(QLabel("Nguồn:"))
        control_layout.addWidget(self.source_combo)
        control_layout.addWidget(QLabel("Đường dẫn:"))
        control_layout.addWidget(self.source_input)
        control_layout.addWidget(QLabel("Độ phân giải:"))
        control_layout.addWidget(self.res_combo)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.pause_btn)

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
        main_vbox.addWidget(self.control_group)
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
        if self.sidebar_layout.count() > 15:
            item = self.sidebar_layout.takeAt(self.sidebar_layout.count() - 1)
            if item:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        # Thêm card mới lên trên cùng của sidebar
        card = DetectionCard(data)
        self.sidebar_layout.insertWidget(0, card)

    def on_source_type_changed(self, text: str) -> None:
        """Tự động ẩn/hiện độ phân giải tùy theo nguồn"""
        is_youtube = text.lower() == "youtube"
        self.res_combo.setEnabled(is_youtube)

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
            source = self.source_input.text()
            source_type = self.source_combo.currentText()
            res = self.res_combo.currentText()

            if not source and source_type.lower() != "webcam":
                return  # Cần có link hoặc đường dẫn

            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.stats_label.setText("📊 THỐNG KÊ: Đang khởi tạo...")

            self.video_thread = VideoThread(
                source, source_type, res, self.stored_detector
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
            self.status_bar.showMessage("Đang tạm dừng - Bạn có thể xem kỹ đoạn này.")

    def update_notification(
        self, message: str, value: int, wait_time_ms: int = 3000
    ) -> None:
        """Cập nhật thanh tiến trình và thông báo cho người dùng"""
        self.status_bar.showMessage(message)
        self.progress_bar.setValue(value)
        if value >= 100:
            # Tự động ẩn progress bar sau n giây khi hoàn thành
            QTimer.singleShot(wait_time_ms, self.progress_bar.hide)

    def save_detector(self, detector_obj: TrafficDetector) -> None:
        """Lưu trữ detector vào MainWindow để dùng lại"""
        self.stored_detector = detector_obj
        print("[+] Đã lưu trữ Model vào bộ nhớ hệ thống.")

    def on_url_changed(self, text: str) -> None:
        """Kiểm tra nếu là link YouTube thì tự động lấy độ phân giải"""
        source_type = self.source_combo.currentText().lower()
        # Chỉ tự động lấy thông tin nếu đang chọn nguồn là YouTube và link có vẻ hợp lệ
        if source_type == "youtube":
            if "youtube.com" in text or "youtu.be" in text:
                self.res_combo.clear()
                self.res_combo.addItem("Đang lấy danh sách...")
                self.res_combo.setEnabled(False)

                # Khởi chạy luồng lấy thông tin ngầm
                self.info_thread = YoutubeInfoThread(text)
                self.info_thread.resolutions_signal.connect(self.update_resolution_list)
                self.info_thread.error_signal.connect(self.on_info_error)
                self.info_thread.start()
            else:
                self.res_combo.clear()
                self.res_combo.setEnabled(False)

    def update_resolution_list(self, resolutions: list[str]) -> None:
        """Cập nhật danh sách độ phân giải thực tế vào ComboBox"""
        self.res_combo.clear()
        resolutions.reverse()
        self.res_combo.addItems(resolutions)
        self.res_combo.setEnabled(True)
        # Tự động chọn độ phân giải cao nhất có sẵn
        if resolutions:
            self.res_combo.setCurrentIndex(0)

    def on_info_error(self, error_msg: str) -> None:
        """Xử lý khi không lấy được thông tin video"""
        self.res_combo.clear()
        self.res_combo.addItem("Lỗi lấy thông tin")
        self.res_combo.setEnabled(False)
        print(f"[!] Lỗi lấy thông tin YouTube: {error_msg}")

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Dừng luồng AI, Giải phóng Camera, Chấp nhận đóng, Tự động gọi"""
        if self.video_thread is not None:
            self.video_thread.stop()
        if event:
            event.accept()
