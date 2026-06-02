"""应用配置 - 集中管理所有可调参数"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class Config:
    """集中管理所有可调参数，避免硬编码魔术数字"""

    # ===== 窗口 =====
    WINDOW_TITLE: str = "mp4toppt"
    WINDOW_WIDTH: int = 900
    WINDOW_HEIGHT: int = 900
    WINDOW_MIN_WIDTH: int = 780
    WINDOW_MIN_HEIGHT: int = 700

    # ===== 默认值 =====
    DEFAULT_INTERVAL: float = 1.0          # 定时截图间隔（秒）
    DEFAULT_STABLE_DURATION: float = 2.0   # 静止检测阈值（秒）
    DEFAULT_SIMILARITY: float = 95.0       # 去重相似度阈值（%）
    SIMILARITY_MIN: float = 1.0
    SIMILARITY_MAX: float = 99.0

    # ===== 图像处理 =====
    HASH_SIZE: int = 8                     # 感知哈希尺寸（8×8）
    HASH_BITS: int = 64                    # HASH_SIZE ** 2
    JPEG_QUALITY: int = 95                 # 截图 JPEG 质量

    # ===== 视频帧采样 =====
    STABLE_SAMPLE_RATIO: float = 0.1       # 静止检测采样频率（相对 fps）

    # ===== 版本 =====
    VERSION: str = "1.0"

    # ===== 支持格式 =====
    SUPPORTED_VIDEO_EXTS: Tuple[str, ...] = field(default_factory=lambda:
        (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"))

    # ===== 依赖包 =====
    DEPENDENCIES: Tuple[str, ...] = field(default_factory=lambda:
        ("cv2", "pptx", "fpdf", "PIL", "customtkinter"))
