from datetime import datetime
from typing import Any

import cv2
import torch
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from traffic_monitor.ai.detector import TrafficDetector
from traffic_monitor.utils.youtube import cap_from_youtube, list_video_streams


class VideoThread(QThread):
    # Gửi thông tin đã xử lý về UI
    change_pixmap_signal = pyqtSignal(QImage)
    # Gửi dictionary chứa: ảnh cắt, tên loại xe, thời gian, độ tin cậy
    new_detection_signal = pyqtSignal(dict)
    # Gửi data thống kê: {"car": 10, "bike": 5}
    stats_signal = pyqtSignal(dict)

    # thêm validate source_type
    def __init__(self, source: str, source_type: str, resolution: str):
        super().__init__()
        self.source = source
        self.source_type = source_type.lower()
        self.resolution = resolution
        self._run_flag = True
        self.last_tracked_ids: set[int] = set()
        # Tổng số lượng theo từng loại xe
        self.counts: dict[str, int] = {}

    def run(self) -> None:
        try:
            # thêm đã load rồi thì không cần load lại nữa
            detector = TrafficDetector()

            cap = None

            if self.source_type == "youtube":
                # thêm chọn độ phân giải từ GUI
                cap = cap_from_youtube(self.source, self.resolution)
            elif self.source_type == "webcam":
                camera_id = int(self.source) if self.source.isdigit() else 0
                cap = cv2.VideoCapture(camera_id)
            elif self.source_type in ["local file", "link mp4", "rtsp camera"]:
                # File local, link .mp4 trực tiếp, hoặc RTSP camera
                cap = cv2.VideoCapture(self.source)
            else:
                raise ValueError(f"Nguồn '{self.source_type}' không được hỗ trợ.")

            if not cap.isOpened():
                print(f"[-] LỖI: Không thể mở nguồn {self.source_type}")
                return

            while self._run_flag:
                success, frame = cap.read()

                if not success:
                    break

                # Xử lý frame bằng YOLO
                results = detector.process_frame(frame)
                if not results:
                    continue

                res = results[0]
                annotated_frame = res.plot()

                if res.boxes is not None and res.boxes.id is not None:
                    ids_raw = res.boxes.id

                    # Kiểm tra nếu là PyTorch Tensor (thường xảy ra khi dùng GPU)
                    if isinstance(ids_raw, torch.Tensor):
                        ids = ids_raw.cpu().numpy().astype(int).tolist()
                    else:
                        # Nếu đã là NumPy array (thường xảy ra khi chạy CPU)
                        ids = ids_raw.astype(int).tolist()

                    for i, obj_id in enumerate(ids):
                        if obj_id not in self.last_tracked_ids:
                            self.last_tracked_ids.add(obj_id)

                            # Đếm xe
                            label = res.names[int(res.boxes[i].cls[0])]
                            self.counts[label] = self.counts.get(label, 0) + 1
                            # Gửi data mới cho UI
                            self.stats_signal.emit(self.counts)

                            # Giới hạn kích thước bộ nhớ ID
                            if len(self.last_tracked_ids) > 100:
                                self.last_tracked_ids.clear()

                            try:
                                # Lấy thông tin box
                                box = res.boxes[i]
                                x1, y1, x2, y2 = box.xyxy[0].int().cpu().tolist()
                                label = res.names[int(box.cls[0])]
                                conf = float(box.conf[0])

                                # Cắt ảnh đối tượng
                                crop = frame[max(0, y1) : y2, max(0, x1) : x2]
                                if crop.size > 0:
                                    self.new_detection_signal.emit(
                                        {
                                            "id": obj_id,
                                            "label": label,
                                            "conf": conf,
                                            "image": crop,
                                            "time": datetime.now().strftime("%H:%M:%S"),
                                        }
                                    )
                            except Exception:
                                pass

                # Chuyển đổi BGR (OpenCV) sang RGB (PyQt)
                rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                # Chiều cao, Chiều rộng, Số kênh
                h, w, ch = rgb_image.shape
                #  Số byte trên mỗi dòng
                bytes_per_line = rgb_image.strides[0]
                qt_image = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
                ).copy()
                self.change_pixmap_signal.emit(qt_image)

            cap.release()
        except Exception as e:
            print(f"[!] LỖI NGHIÊM TRỌNG TRONG THREAD: {e}")

    def stop(self) -> None:
        self._run_flag = False
        self.wait()


class YoutubeInfoThread(QThread):
    # Gửi về danh sách độ phân giải (list các chuỗi)
    resolutions_signal = pyqtSignal(list)
    # Gửi về lỗi
    error_signal = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            # Gọi hàm lấy stream từ utils
            _, resolutions = list_video_streams(self.url)
            # Chuyển từ numpy array sang list để gửi về UI
            self.resolutions_signal.emit(resolutions.tolist())
        except Exception as e:
            self.error_signal.emit(str(e))


class DetectionCard(QFrame):
    """Widget hiển thị một đối tượng trong Sidebar"""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "background-color: #2c2c2c; border-radius: 5px; margin: 2px; color: white;"
        )
        layout = QHBoxLayout(self)

        # Ảnh cắt
        img_label = QLabel()
        h, w, ch = data["image"].shape
        qimg = QImage(
            cv2.cvtColor(data["image"], cv2.COLOR_BGR2RGB).data,
            w,
            h,
            w * ch,
            QImage.Format.Format_RGB888,
        ).copy()
        img_label.setPixmap(
            QPixmap.fromImage(qimg).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)
        )

        # Thông tin văn bản
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"ID: {data['id']} - {data['label']}"))
        info_layout.addWidget(QLabel(f"Conf: {data['conf']:.2f}"))
        info_layout.addWidget(QLabel(f"Time: {data['time']}"))

        layout.addWidget(img_label)
        layout.addLayout(info_layout)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hệ thống giám sát Giao thông")
        self.resize(1300, 800)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.video_thread: VideoThread | None = None

        # Layout chính
        main_vbox = QVBoxLayout()

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

        # Nút Start/Stop
        self.start_btn = QPushButton("Bắt đầu")
        self.start_btn.clicked.connect(self.toggle_detection)
        self.start_btn.setStyleSheet(
            "background-color: #2e7d32; color: white; font-weight: bold;"
        )

        control_layout.addWidget(QLabel("Nguồn:"))
        control_layout.addWidget(self.source_combo)
        control_layout.addWidget(QLabel("Đường dẫn:"))
        control_layout.addWidget(self.source_input)
        control_layout.addWidget(QLabel("Độ phân giải:"))
        control_layout.addWidget(self.res_combo)
        control_layout.addWidget(self.start_btn)

        # Ngang (Video | Sidebar)
        content_layout = QHBoxLayout()

        # Video Area
        self.video_label = QLabel("Đang tải stream...")
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

        main_vbox.addWidget(self.stats_widget)
        main_vbox.addWidget(self.control_group)
        main_vbox.addLayout(content_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_vbox)
        self.setCentralWidget(central_widget)

    def update_stats(self, counts: dict[str, int]) -> None:
        """Cập nhật dòng chữ thống kê trên Dashboard"""
        stat_items = [f"{label.upper()}: {value}" for label, value in counts.items()]
        display_text = "  |  ".join(stat_items)
        self.stats_label.setText(f"📊 THỐNG KÊ: {display_text}")

    def update_image(self, qt_image: QImage) -> None:
        # Cập nhật khung hình lên giao diện
        pixmap = QPixmap.fromImage(qt_image)
        # Tự động co giãn ảnh theo kích thước cửa sổ nhưng giữ tỉ lệ
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled_pixmap)

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
        """Xử lý sự kiện nhấn nút Bắt đầu / Dừng lại"""
        if self.video_thread is not None and self.video_thread.isRunning():
            # Nếu đang chạy thì dừng lại
            self.video_thread.stop()
            self.start_btn.setText("Bắt đầu")
            self.start_btn.setStyleSheet("background-color: #2e7d32; color: white;")
            self.video_label.setText("Đã dừng.")
        else:
            # Nếu đang dừng thì bắt đầu luồng mới
            source = self.source_input.text()
            source_type = self.source_combo.currentText()
            res = self.res_combo.currentText()

            if not source and source_type.lower() != "webcam":
                return  # Cần có link hoặc đường dẫn

            self.video_thread = VideoThread(source, source_type, res)
            self.video_thread.change_pixmap_signal.connect(self.update_video)
            self.video_thread.new_detection_signal.connect(self.add_detection_card)
            self.video_thread.stats_signal.connect(self.update_stats)
            self.video_thread.start()

            self.start_btn.setText("Dừng lại")
            self.start_btn.setStyleSheet("background-color: #c62828; color: white;")

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
