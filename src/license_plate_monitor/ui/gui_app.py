from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import Qt, QTimer

from license_plate_monitor.ui.threads import VideoThread, YoutubeInfoThread
from license_plate_monitor.ui.widgets import (
    AISettingTab,
    DetectionSidebar,
    SettingsDock,
    SourceTab,
    StatsDock,
)

if TYPE_CHECKING:
    from license_plate_monitor.ai.detector import LicensePlateDetector
from PyQt6.QtGui import QAction, QCloseEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._init_ui_settings()
        self._create_widgets()
        self._setup_layouts()
        self._setup_docks_and_menus()
        self._connect_signals()

        # Nút Start/Stop
        self.start_btn.setStyleSheet(
            "background-color: #2e7d32; color: white; font-weight: bold;"
        )

        # Nút Tạm dừng
        self.pause_btn.setEnabled(False)

        # Clear History Button
        self.clear_btn.setStyleSheet("background-color: #444; color: white;")
        self.clear_btn.setEnabled(False)

    def _init_ui_settings(self) -> None:
        self.setWindowTitle("License Plate Monitor System")
        self.resize(1300, 800)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.video_thread: VideoThread | None = None
        self.stored_detector: LicensePlateDetector | None = None

    def _create_widgets(self) -> None:
        # Video & Sidebar
        self.video_label = QLabel("Đang chờ bắt đầu...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar = DetectionSidebar()

        # Tabs
        self.tabs = QTabWidget()
        self.source_tab = SourceTab()
        self.ai_tab = AISettingTab()
        self.tabs.addTab(self.source_tab, "📡 Nguồn Video")
        self.tabs.addTab(self.ai_tab, "🤖 Cấu hình AI")

        # Actions & Status
        self.start_btn = QPushButton("Bắt đầu")
        self.pause_btn = QPushButton("Tạm dừng")
        self.clear_btn = QPushButton("Xóa lịch sử")

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

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng.")
        self.status_bar.setStyleSheet("font-size: 14px;")

        # Dock Widgets
        self.dock_settings = SettingsDock(self)
        self.dock_settings.setWidget(self.tabs)
        self.stats_dock = StatsDock(self)

    def _setup_layouts(self) -> None:
        # Action Layout
        action_group = QGroupBox("Thao tác nhanh")
        action_layout = QHBoxLayout(action_group)
        action_layout.addWidget(self.start_btn)
        action_layout.addWidget(self.pause_btn)
        action_layout.addWidget(self.clear_btn)

        # Content Layout (Video + Sidebar)
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.video_label, stretch=4)
        content_layout.addWidget(self.sidebar, stretch=1)

        # Main Layout
        main_vbox = QVBoxLayout()
        main_vbox.addWidget(action_group)
        main_vbox.addWidget(self.progress_bar)
        main_vbox.addLayout(content_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_vbox)
        self.setCentralWidget(central_widget)

    def _setup_docks_and_menus(self) -> None:
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.stats_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_settings)

        menu_bar = cast(QMenuBar, self.menuBar())
        view_menu = cast(QMenu, menu_bar.addMenu("Hiển thị"))

        show_settings_action = cast(QAction, self.dock_settings.toggleViewAction())
        show_settings_action.setText("Bảng cài đặt")

        stats_toggle_action = cast(QAction, self.stats_dock.toggleViewAction())
        stats_toggle_action.setText("Bảng thống kê")

        # Gắn toggle actions vào Menu
        view_menu.addAction(self.dock_settings.toggleViewAction())
        view_menu.addAction(self.stats_dock.toggleViewAction())

    def _connect_signals(self) -> None:
        self.start_btn.clicked.connect(self.toggle_detection)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.clear_btn.clicked.connect(self.sidebar.clear_history)

        self.source_tab.combo.currentTextChanged.connect(self.on_source_type_changed)
        self.source_tab.input.textChanged.connect(self.on_url_changed)

    def update_stats(self, counts: dict[str, int]) -> None:
        """Cập nhật dòng chữ thống kê trên Dashboard"""
        stat_items = [f"{label.upper()}: {value}" for label, value in counts.items()]
        display_text = "  |  ".join(stat_items)
        self.stats_dock.update_text(f"📊 THỐNG KÊ: {display_text}")

    def update_video(self, qt_image: QImage) -> None:
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

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

            self.sidebar.clear_history()

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
            self.stats_dock.update_text("📊 THỐNG KÊ: Đang chờ dữ liệu...")

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
            self.video_thread.new_detection_signal.connect(self.sidebar.add_card)
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
