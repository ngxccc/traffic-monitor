from datetime import datetime

import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from traffic_monitor.ai.detector import TrafficDetector
from traffic_monitor.utils.youtube import cap_from_youtube, list_video_streams


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
        detector: TrafficDetector | None = None,
    ):
        super().__init__()
        self.source = source
        self.source_type = source_type.lower()
        self.resolution = resolution
        self.detector = detector
        self._run_flag = True
        self.last_tracked_ids: set[int] = set()
        # Tổng số lượng theo từng loại xe
        self.counts: dict[str, int] = {}

    def run(self) -> None:
        try:
            if self.detector is None:
                # Conditional Import giúp tối ưu việc import và hiệu năng
                from traffic_monitor.ai.detector import TrafficDetector

                print("[*] Đang nạp Model lần đầu tiên...")
                self.progress_signal.emit("Đang nạp mô hình AI...", 20)
                self.detector = TrafficDetector()
                self.progress_signal.emit("Nạp mô hình thành công!", 100)
                self.detector_ready_signal.emit(self.detector)
            else:
                print("[*] Sử dụng Model đã nạp sẵn.")

            self.progress_signal.emit(f"Đang kết nối tới {self.source_type}...", 50)

            cap = None

            if self.source_type == "youtube":
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

            self.progress_signal.emit("Bắt đầu nhận diện!", 100)

            while self._run_flag:
                success, frame = cap.read()

                if not success:
                    break

                # Xử lý frame bằng YOLO
                results = self.detector.process_frame(frame)
                if not results:
                    continue

                res = results[0]
                annotated_frame = res.plot()

                if res.boxes is not None and res.boxes.id is not None:
                    ids_raw = res.boxes.id

                    # Kiểm tra nếu là PyTorch Tensor (thường xảy ra khi dùng GPU)
                    import torch

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
