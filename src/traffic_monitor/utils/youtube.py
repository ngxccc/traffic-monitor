import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np
import numpy.typing as npt
import yt_dlp

# Cấu hình logging để theo dõi lỗi thay vì chỉ print
logger = logging.getLogger(__name__)

VALID_RESOLUTIONS = [
    "144p",
    "240p",
    "360p",
    "480p",
    "720p",
    "720p60",
    "1080p",
    "1080p60",
    "1440p",
    "1440p60",
    "2160p",
    "2160p60",
]


@dataclass
class VideoStream:
    url: str
    resolution: str
    height: int
    width: int

    @classmethod
    def from_dict(cls, video_format: dict[str, Any]) -> "VideoStream":
        """Factory method để tạo VideoStream từ dict của yt-dlp."""
        return cls(
            url=video_format["url"],
            resolution=video_format.get("format_note", "unknown"),
            height=video_format.get("height", 0),
            width=video_format.get("width", 0),
        )

    def __str__(self) -> str:
        return f"{self.resolution} ({self.height}x{self.width})"


def list_video_streams(
    url: str, ydl_opts: Optional[dict[str, Any]] = None
) -> Tuple[List[VideoStream], npt.NDArray[np.str_]]:
    """
    Lấy danh sách các luồng video có sẵn từ URL YouTube.
    """
    opts = ydl_opts or {}

    # tuỳ chọn 'deno', node', 'bun'
    opts.setdefault(
        "js_runtimes",
        {
            "deno": {},
            "bun": {},
            "node": {},
        },
    )

    # Cho phép tải script từ npm/github nếu gói local không khả dụng
    opts.setdefault("remote_components", ["ejs:npm", "ejs:github"])

    # Mặc định không tải video, chỉ lấy thông tin
    opts.setdefault("quiet", True)
    opts.setdefault("no_warnings", True)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ValueError("Không thể lấy thông tin từ URL.")

            # Lọc các format có cả video và link trực tiếp (không phải SABR nếu có thể)
            formats = info.get("formats", [])

            def is_valid(f: dict[str, Any]) -> bool:
                return (
                    f.get("vcodec") != "none"
                    # and f.get("acodec")
                    # != "none"  # Không lấy âm thanh gì > 360p không hỗ trợ
                    and f.get("format_note") in VALID_RESOLUTIONS
                )

            streams = [VideoStream.from_dict(f) for f in formats[::-1] if is_valid(f)]

            # Loại bỏ trùng lặp độ phân giải, giữ lại bản tốt nhất mỗi loại
            _, unique_indices = np.unique(
                np.array([s.resolution for s in streams]), return_index=True
            )
            streams = [streams[i] for i in np.sort(unique_indices)]

            resolutions = np.array([s.resolution for s in streams], dtype=np.str_)
            return streams[::-1], resolutions[::-1]

    except Exception as e:
        logger.error(f"Lỗi khi truy xuất stream: {e}")
        raise


def cap_from_youtube(
    url: str,
    resolution: str = "best",
    start: timedelta = timedelta(seconds=0),
    use_cookies: bool = False,
) -> cv2.VideoCapture:
    """
    Tạo đối tượng cv2.VideoCapture từ URL YouTube.

    Args:
        url: Link video YouTube.
        resolution: 'best' hoặc độ phân giải cụ thể (vd: '720p').
        start: Thời điểm bắt đầu video.
        use_cookies: Nếu True, sẽ tìm file cookies.txt trong thư mục gốc để tránh bị chặn.
    """  # noqa: E501
    ydl_opts: dict[str, Any] = {}
    if use_cookies:
        # Tự động tìm file cookies nếu bạn để trong project
        ydl_opts["cookiefile"] = "cookies.txt"

    streams, resolutions = list_video_streams(url, ydl_opts)

    if resolution == "best":
        target_res = resolutions[-1]
    elif resolution not in resolutions:
        logger.warning(f"Độ phân giải {resolution} không có sẵn. Chọn 'best'.")
        target_res = resolutions[-1]
    else:
        target_res = resolution

    # Tìm index của độ phân giải đã chọn
    idx = int(np.where(resolutions == target_res)[0][0])
    stream_url = streams[idx].url

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        raise ConnectionError("Không thể mở luồng video từ URL đã lấy.")

    # Thiết lập thời điểm bắt đầu
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps > 0:
        start_frame = int(start.total_seconds() * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    return cap
