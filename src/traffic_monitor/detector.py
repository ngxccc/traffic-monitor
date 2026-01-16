from typing import Any

import numpy.typing as npt
from ultralytics import YOLO
from ultralytics.engine.results import Results


class TrafficDetector:
    def __init__(self, model_name: str = "models/yolo11n.pt"):
        self.model = YOLO(model_name)

    def process_frame(self, frame: npt.NDArray[Any]) -> list[Results]:
        results = self.model.track(
            frame, persist=True, tracker="bytetrack.yaml", verbose=False
        )
        return results
