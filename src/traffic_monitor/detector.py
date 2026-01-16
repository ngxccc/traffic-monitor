from typing import Any

import numpy.typing as npt
from ultralytics import YOLO
from ultralytics.engine.results import Results


class TrafficDetector:
    def __init__(self, model_name: str = r"models\yolo11n_int8_openvino_model"):
        self.model = YOLO(model_name, task="detect")

    def process_frame(self, frame: npt.NDArray[Any]) -> list[Results]:
        results = self.model.track(
            frame, persist=True, tracker="bytetrack.yaml", verbose=False
        )
        return results
