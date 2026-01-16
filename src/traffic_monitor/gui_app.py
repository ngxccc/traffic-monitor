from datetime import datetime
from typing import Any

import cv2
import torch
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from traffic_monitor.detector import TrafficDetector
from traffic_monitor.utils.youtube import cap_from_youtube


class VideoThread(QThread):
    # Signal để gửi thông tin đã xử lý về UI
    change_pixmap_signal = pyqtSignal(QImage)
    # Gửi dictionary chứa: ảnh cắt, tên loại xe, thời gian, độ tin cậy
    new_detection_signal = pyqtSignal(dict)

    def __init__(self, ytb_url: str):
        super().__init__()
        self.ytb_url = ytb_url
        self._run_flag = True
        self.last_tracked_ids: set[int] = set()

    def run(self) -> None:
        try:
            detector = TrafficDetector()

            cap = cap_from_youtube(self.ytb_url, "720p")

            if not cap.isOpened():
                print("[-] LỖI: Không thể mở luồng video.")
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

        # Layout chính: Ngang (Video | Sidebar)
        main_layout = QHBoxLayout()

        # Video Area
        self.video_label = QLabel("Đang tải stream...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.video_label, stretch=4)  # Chiếm 4 phần diện tích

        # Sidebar Area
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_container = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFixedWidth(300)
        self.sidebar_scroll.setWidget(self.sidebar_container)
        main_layout.addWidget(self.sidebar_scroll, stretch=1)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        url = "https://www.youtube.com/watch?v=4aWufTZDLMU"
        self.video_thread = VideoThread(url)
        self.video_thread.change_pixmap_signal.connect(self.update_video)
        self.video_thread.new_detection_signal.connect(self.add_detection_card)
        self.video_thread.start()

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

    def closeEvent(self, event: QCloseEvent | None) -> None:
        # self.video_thread._run_flag = False
        # self.video_thread.wait()
        self.video_thread.stop()
        if event:
            event.accept()
