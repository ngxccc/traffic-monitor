import os
from datetime import datetime

import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from license_plate_monitor.ai.detector import LicensePlateDetector
from license_plate_monitor.utils.youtube import cap_from_youtube, list_video_streams


class VideoThread(QThread):
    # Gửi thông tin đã xử lý về UI
    change_pixmap_signal = pyqtSignal(QImage)
    # Gửi dictionary chứa: ảnh cắt, tên loại xe, thời gian, độ tin cậy
    new_detection_signal = pyqtSignal(dict)
    # Gửi data thống kê: {"car": 10, "bike": 5}
    stats_signal = pyqtSignal(dict)
    # Gửi lại đối tượng detector sau khi nạp thành công
    detector_ready_signal = pyqtSignal(object)
    # Gửi trạng thái nạp mô hình (0-100%) hoặc tin nhắn thông báo
    progress_signal = pyqtSignal(str, int)

    def __init__(
        self,
        source: str,
        source_type: str,
        resolution: str,
        detector: LicensePlateDetector | None = None,
        conf_threshold: float = 0.5,
        show_labels: bool = True,
        show_boxes: bool = True,
        auto_save: bool = False,
    ):
        super().__init__()
        self.source = source
        self.source_type = source_type.lower()
        self.resolution = resolution
        self.detector = detector
        self._run_flag = True
        self._is_paused = False
        # Tổng số lượng theo từng loại xe
        self.counts: dict[str, int] = {}
        self.conf_threshold = conf_threshold
        self.show_labels = show_labels
        self.show_boxes = show_boxes
        self.auto_save = auto_save
        self.save_dir = "detections"

        if self.auto_save and not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def _initialize_detector(self) -> None:
        """Helper để nạp mô hình AI"""
        if self.detector is None:
            self.progress_signal.emit("Đang nạp mô hình AI...", 20)
            self.detector = LicensePlateDetector()
            self.progress_signal.emit("Nạp mô hình thành công!", 100)
            self.detector_ready_signal.emit(self.detector)
        else:
            print("[*] Sử dụng Model đã nạp sẵn.")

    def _setup_capture(self) -> cv2.VideoCapture:
        """Helper để khởi tạo cv2.VideoCapture dựa trên loại nguồn"""
        self.progress_signal.emit(f"Đang kết nối tới {self.source_type}...", 50)

        if self.source_type == "youtube":
            return cap_from_youtube(self.source, self.resolution)

        if self.source_type == "webcam":
            camera_id = int(self.source) if self.source.isdigit() else 0
            return cv2.VideoCapture(camera_id)

        if self.source_type in ["local file", "link mp4", "rtsp camera"]:
            return cv2.VideoCapture(self.source)

        raise ValueError(f"Nguồn '{self.source_type}' không được hỗ trợ.")

    def run(self) -> None:
        try:
            self._initialize_detector()

            cap = self._setup_capture()

            if not cap.isOpened():
                error_msg = f"Không thể mở nguồn: {self.source_type}"
                self.progress_signal.emit(f"[-] LỖI: {error_msg}", 0)
                print(f"[-] {error_msg}")
                return

            self.progress_signal.emit("Bắt đầu nhận diện!", 100)

            while self._run_flag:
                if self._is_paused:
                    self.msleep(100)
                    continue

                success, frame = cap.read()

                if not success:
                    print("[!] Mất kết nối. Đang thử kết nối lại...")
                    cap.release()
                    self.msleep(1000)
                    cap = self._setup_capture()
                    if not cap.isOpened():
                        continue
                    success, frame = cap.read()
                    if not success:
                        break

                h, w = frame.shape[:2]

                # Xử lý frame bằng YOLO
                if self.detector is None:
                    break
                annotated_frame, detections = self.detector.process_frame(
                    frame, self.conf_threshold, self.show_labels, self.show_boxes
                )

                for det in detections:
                    # Cập nhật thống kê xe
                    label = det["label"]
                    self.counts[label] = self.counts.get(label, 0) + 1
                    self.stats_signal.emit(self.counts)

                    # Gửi data về UI (bổ sung thêm timestamp tại thread)
                    det["time"] = datetime.now().strftime("%H:%M:%S")

                    if self.auto_save:
                        try:
                            # Tạo tên file: label_id_timestamp.png
                            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
                            filename = f"{det['label']}_{det['id']}_{timestamp}.png"
                            filepath = os.path.join(self.save_dir, filename)

                            # Nếu ảnh là RGB cần chuyển lại BGR
                            # cv2.cvtColor(det["image"], cv2.COLOR_RGB2BGR
                            cv2.imwrite(filepath, det["image"])
                        except Exception as e:
                            print(f"Lỗi khi lưu ảnh: {e}")
                    self.new_detection_signal.emit(det)

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

        except Exception as e:
            error_info = f"LỖI KHỞI TẠO: {str(e)}"
            self.progress_signal.emit(error_info, 0)
            print(f"[!] {error_info}")
        finally:
            if "cap" in locals() and cap is not None:
                cap.release()

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

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
