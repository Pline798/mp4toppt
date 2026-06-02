"""文件校验与工具函数"""

import re
import tempfile
import shutil
from pathlib import Path
from typing import Union

import cv2

from config import Config

VALIDATOR_CHARS = re.compile(r'[<>:"/\\|?*]')


def is_valid_video_file(file_path: Union[str, Path]) -> bool:
    """检查文件是否为受支持的、可打开的视频文件"""
    ext = Path(file_path).suffix.lower()
    if ext not in Config.SUPPORTED_VIDEO_EXTS:
        return False
    try:
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            return False
        cap.release()
        return True
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    return VALIDATOR_CHARS.sub("_", name)


def format_file_size(size_bytes: Union[int, float]) -> str:
    """人性化显示文件大小（B/KB/MB/GB）"""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def cleanup_stale_temp():
    """启动时清理上次残留的临时目录"""
    temp_dir = Path(tempfile.gettempdir())
    for d in temp_dir.glob("video2ppt_*"):
        try:
            shutil.rmtree(str(d))
        except Exception:
            pass


def robust_rmtree(path: Union[str, Path], max_retries: int = 3):
    """健壮地递归删除目录，处理 Windows 文件锁"""
    for attempt in range(max_retries):
        try:
            shutil.rmtree(str(path))
            return
        except Exception:
            if attempt < max_retries - 1:
                import time
                time.sleep(0.5)
            else:
                raise
