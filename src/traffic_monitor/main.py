import cv2

from traffic_monitor.detector import TrafficDetector
from traffic_monitor.utils.youtube import cap_from_youtube


def main() -> None:
    window_name = "Traffic Monitor"
    youtube_url = "https://www.youtube.com/watch?v=4aWufTZDLMU"

    cap = cap_from_youtube(youtube_url, "1080p")
    detector = TrafficDetector()

    # Khởi tạo cửa sổ có khả năng co giãn, giữ nguyên khung hình
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    # Đặt kích thước mặc định ban đầu
    cv2.resizeWindow(window_name, 1280, 700)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        results = detector.process_frame(frame)
        annotated_frame = results[0].plot()

        cv2.imshow(window_name, annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
