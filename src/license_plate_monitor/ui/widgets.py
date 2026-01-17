from typing import Any

import cv2
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


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
