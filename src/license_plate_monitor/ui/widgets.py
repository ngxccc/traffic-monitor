from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class DetectionCard(QFrame):
    """Widget hiển thị một đối tượng trong Sidebar"""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__()
        self.setup_ui(data)

    def setup_ui(self, data: dict[str, Any]) -> None:
        self.setStyleSheet("""
            DetectionCard {
                background-color: #2c2c2c;
                border-radius: 8px;
                border: 1px solid #444;
                margin-bottom: 5px;
            }
            DetectionCard:hover {
                background-color: #3d3d3d;
                border: 1px solid #3498db;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Hiển thị ảnh cắt
        img_label = QLabel()
        img_label.setFixedSize(80, 80)

        h, w, ch = data["image"].shape
        qimg = QImage(
            data["image"].tobytes(), w, h, w * ch, QImage.Format.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qimg).scaled(
            80,
            80,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        img_label.setPixmap(pixmap)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Thông tin chi tiết
        info_layout = QVBoxLayout()
        id_label = QLabel(f"<b>ID: {data['id']}</b> | {data['label'].upper()}")
        id_label.setStyleSheet("color: #3498db; font-size: 13px; margin-left: 10px;")

        conf_label = QLabel(f"Độ tin cậy: {data['conf']:.2f}")
        conf_label.setStyleSheet("color: #bbb; font-size: 11px; margin-left: 10px;")

        time_label = QLabel(f"{data['time']}")
        time_label.setStyleSheet("color: #888; font-size: 11px; margin-left: 10px;")

        info_layout.addWidget(id_label)
        info_layout.addWidget(conf_label)
        info_layout.addWidget(time_label)

        layout.addWidget(img_label)
        layout.addLayout(info_layout)


class SourceTab(QWidget):
    """Quản lý cấu hình nguồn vào"""

    def __init__(self) -> None:
        super().__init__()
        layout = QGridLayout(self)

        self.combo = QComboBox()
        self.combo.addItems(["YouTube", "Webcam", "Local File", "RTSP"])
        self.combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Nhập URL YouTube hoặc đường dẫn file...")

        self.res_combo = QComboBox()
        self.res_combo.setEnabled(False)
        self.res_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        layout.addWidget(QLabel("Loại nguồn:"), 0, 0)
        layout.addWidget(self.combo, 0, 1)
        layout.addWidget(QLabel("Đường dẫn:"), 1, 0)
        layout.addWidget(self.input, 1, 1)
        layout.addWidget(QLabel("Độ phân giải:"), 2, 0)
        layout.addWidget(self.res_combo, 2, 1)


class AISettingTab(QWidget):
    """Quản lý các thông số AI và lưu trữ"""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.65)

        self.show_labels = QCheckBox("Hiện nhãn văn bản")
        self.show_labels.setStyleSheet("color: white;")

        self.show_boxes = QCheckBox("Hiện khung bao (Boxes)")
        self.show_boxes.setStyleSheet("color: white;")

        self.auto_save = QCheckBox("Tự động lưu ảnh vào máy")
        self.auto_save.setStyleSheet("color: white;")
        self.auto_save.setToolTip("Lưu ảnh cắt biển số vào thư mục 'detections'")
        self.auto_save.setChecked(True)

        layout.addWidget(QLabel("Độ tin cậy (Confidence):"))
        layout.addWidget(self.conf_spin)
        layout.addWidget(self.show_labels)
        layout.addWidget(self.show_boxes)
        layout.addWidget(self.auto_save)
        layout.addStretch()
