"""视频帧提取引擎 - 支持定时截图和静止检测两种模式"""

from typing import Callable, List, Optional, Tuple
import cv2
import os

from config import Config


class VideoEngine:
    """视频帧提取引擎，负责从视频中智能提取关键帧"""

    def __init__(self, screenshot_mode: str = "interval", interval: float = 1.0,
                 stable_duration: float = 2.0, similarity_threshold: float = 95.0):
        self.screenshot_mode = screenshot_mode
        self.interval = interval
        self.stable_duration = stable_duration
        self.similarity_threshold = similarity_threshold

    # ---- 感知哈希 ----

    def _compute_hash(self, frame) -> str:
        """计算帧的感知哈希（pHash），用于快速比较"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (Config.HASH_SIZE, Config.HASH_SIZE),
                             interpolation=cv2.INTER_AREA)
        avg = resized.mean()
        return "".join("1" if p > avg else "0" for p in resized.flatten())

    @staticmethod
    def _hamming_similarity(hash1: str, hash2: str) -> float:
        """计算两个感知哈希的相似度百分比"""
        diff = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        return (1 - diff / Config.HASH_BITS) * 100

    # ---- 帧提取 ----

    def extract_frames_by_interval(
        self, video_path: str, temp_dir: str,
        progress_callback: Callable[[float, int, int], None]
    ) -> Tuple[Optional[List[str]], Optional[int], Optional[int]]:
        """定时截图模式：按固定间隔截图并去重

        Returns:
            (temp_images列表, 截图数, 去重数) 或 (None, None, None) 表示失败
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, None, None

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps * self.interval))

        frame_count = 0
        screenshot_count = 0
        duplicate_count = 0
        temp_images: List[str] = []
        last_hash: Optional[str] = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                current_hash = self._compute_hash(frame)
                is_duplicate = False
                if last_hash is not None:
                    similarity = self._hamming_similarity(last_hash, current_hash)
                    if similarity >= self.similarity_threshold:
                        is_duplicate = True
                        duplicate_count += 1

                if not is_duplicate:
                    temp_img = os.path.join(temp_dir, f"frame_{screenshot_count:05d}.jpg")
                    cv2.imwrite(temp_img, frame, [cv2.IMWRITE_JPEG_QUALITY, Config.JPEG_QUALITY])
                    temp_images.append(temp_img)
                    screenshot_count += 1
                    last_hash = current_hash

                progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                progress_callback(progress, screenshot_count, duplicate_count)

            frame_count += 1

        cap.release()
        return temp_images, screenshot_count, duplicate_count

    def extract_frames_by_stable(
        self, video_path: str, temp_dir: str,
        progress_callback: Callable[[float, int, int], None]
    ) -> Tuple[Optional[List[str]], Optional[int], Optional[int]]:
        """静止检测模式：画面静止超过阈值时自动截图

        修复记录：V4 版本中 check_interval 未除以 frame_interval，
        导致实际需要的静止时长约为用户设定值的 6 倍。
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, None, None

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps * Config.STABLE_SAMPLE_RATIO))
        # V1 Bug fix: 除以 frame_interval 使实际静止时长匹配用户设定值
        check_interval = max(1, int(fps * self.stable_duration / frame_interval))

        frame_count = 0
        screenshot_count = 0
        duplicate_count = 0
        temp_images: List[str] = []
        last_hash: Optional[str] = None
        consecutive_similar = 0
        last_screenshot_frame = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                current_hash = self._compute_hash(frame)
                should_screenshot = False
                is_duplicate = False

                if last_hash is not None:
                    similarity = self._hamming_similarity(last_hash, current_hash)
                    if similarity >= self.similarity_threshold:
                        is_duplicate = True
                        duplicate_count += 1
                        consecutive_similar += 1
                        if consecutive_similar >= check_interval:
                            frames_since_last = frame_count - last_screenshot_frame
                            if frames_since_last / fps >= self.stable_duration:
                                should_screenshot = True
                    else:
                        consecutive_similar = 0
                else:
                    # 第一帧：直接截图
                    should_screenshot = True

                if should_screenshot:
                    temp_img = os.path.join(temp_dir, f"frame_{screenshot_count:05d}.jpg")
                    cv2.imwrite(temp_img, frame, [cv2.IMWRITE_JPEG_QUALITY, Config.JPEG_QUALITY])
                    temp_images.append(temp_img)
                    screenshot_count += 1
                    last_screenshot_frame = frame_count
                    consecutive_similar = 0
                    last_hash = current_hash

                if not is_duplicate:
                    last_hash = current_hash

                progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                progress_callback(progress, screenshot_count, duplicate_count)

            frame_count += 1

        cap.release()
        return temp_images, screenshot_count, duplicate_count

    def extract_frames(
        self, video_path: str, temp_dir: str,
        progress_callback: Callable[[float, int, int], None]
    ) -> Tuple[Optional[List[str]], Optional[int], Optional[int]]:
        """统一入口，按当前模式提取帧"""
        if self.screenshot_mode == "interval":
            return self.extract_frames_by_interval(video_path, temp_dir, progress_callback)
        return self.extract_frames_by_stable(video_path, temp_dir, progress_callback)
