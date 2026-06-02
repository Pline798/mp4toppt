"""转换任务管理 - 协调引擎和生成器完成视频批处理"""

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.engine import VideoEngine
from core.generator import FileGenerator
from core.validator import sanitize_filename, robust_rmtree


class ConversionTask:
    """一次转换任务，管理视频列表中每个文件的帧提取和文档生成"""

    def __init__(self, video_paths: List[str], output_dir: str,
                 format_ext: str, engine: VideoEngine, callbacks: Dict[str, Callable]):
        """
        Args:
            callbacks: {
                'on_status': func(message),
                'on_progress': func(percent),
                'on_file_status': func(path, status),
                'on_file_detail': func(path, detail_dict),
                'should_cancel': func() -> bool,
            }
        """
        self.video_paths = video_paths
        self.output_dir = output_dir
        self.format_ext = format_ext
        self.format_name = "PPT" if format_ext == "pptx" else "PDF"
        self.engine = engine
        self.cb = callbacks

    def _safe_call(self, key: str, *args):
        """安全调用可选回调"""
        fn = self.cb.get(key)
        if fn:
            fn(*args)

    def run(self, temp_dir: str) -> Tuple[int, int, List[Tuple[str, str]]]:
        """执行全部视频的帧提取和文档生成"""
        total_videos = len(self.video_paths)
        mode_name = "定时截图" if self.engine.screenshot_mode == "interval" else "静止检测"
        success_count = 0
        fail_count = 0
        results: List[Tuple[str, str]] = []

        for idx, video_path in enumerate(self.video_paths):
            if self.cb.get('should_cancel') and self.cb['should_cancel']():
                self._safe_call('on_status', "转换已取消")
                break

            self._safe_call('on_file_status', video_path, "processing")
            video_name = sanitize_filename(Path(video_path).stem)
            output_file = Path(self.output_dir) / f"{video_name}.{self.format_ext}"
            self._safe_call('on_status', f"正在处理 ({idx+1}/{total_videos}): {video_name}")

            def _build_progress_cb(current_idx: int) -> Callable:
                def cb(progress: float, screenshot_count: int, duplicate_count: int):
                    self._safe_call('on_status',
                        f"[{mode_name}] 已截取 {screenshot_count} 张 "
                        f"(去重 {duplicate_count} 张, {progress:.1f}%)")
                    overall = ((current_idx + progress / 100) / total_videos) * 100
                    self._safe_call('on_progress', overall)
                return cb

            temp_images, screenshot_count, duplicate_count = self.engine.extract_frames(
                video_path, temp_dir, _build_progress_cb(idx)
            )

            if temp_images is None:
                self._safe_call('on_status', f"错误: 无法打开视频 {video_name}")
                self._safe_call('on_file_status', video_path, "failed")
                fail_count += 1
                results.append((video_name, "❌ 无法打开视频"))
                continue

            if not temp_images:
                self._safe_call('on_status', f"警告: {video_name} 没有可用的图片")
                self._safe_call('on_file_status', video_path, "failed")
                fail_count += 1
                results.append((video_name, "❌ 无可用图片"))
                continue

            if output_file.exists():
                self._safe_call('on_status', f"提示: 文件已存在，将覆盖 {video_name}")

            self._safe_call('on_status', f"正在生成{self.format_name} ({idx+1}/{total_videos}): {video_name}")
            FileGenerator.generate(temp_images, self.format_ext, str(output_file))

            # 清理临时图片
            for img_path in temp_images:
                p = Path(img_path)
                if p.exists():
                    p.unlink(missing_ok=True)

            self._safe_call('on_file_status', video_path, "completed")
            self._safe_call('on_file_detail', video_path, {
                "screenshots": screenshot_count,
                "duplicates": duplicate_count,
            })
            success_count += 1
            results.append((video_name, f"✅ {screenshot_count} 张截图"))
            self._safe_call('on_progress', ((idx + 1) / total_videos) * 100)

        self._safe_call('on_progress', 100)
        # 清理临时目录
        try:
            robust_rmtree(temp_dir)
        except Exception:
            pass
        return success_count, fail_count, results
