"""主应用类 - mp4toppt 图形界面"""

import os
import subprocess
import threading
import tempfile
from pathlib import Path
from typing import Dict, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from config import Config
from config.themes import THEMES
from core.validator import (
    is_valid_video_file, sanitize_filename, format_file_size,
    cleanup_stale_temp,
)
from core.deps import check_dependencies
from core.converter import ConversionTask
from core.engine import VideoEngine
from ui.widgets import OptionCard, PulseAnimation
from ui import dialogs


class VideoConverterFluent:
    """视频转换主窗口"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(Config.WINDOW_TITLE)
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.root.minsize(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT)

        # 窗口图标
        icon_path = Path(__file__).parent.parent / "icon.png"
        if icon_path.exists():
            try:
                import tkinter as tk
                tk_img = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, tk_img)
            except Exception:
                pass

        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - Config.WINDOW_WIDTH) // 2
        y = (sh - Config.WINDOW_HEIGHT) // 2
        self.root.geometry(f"+{x}+{y}")

        # 状态变量
        self.video_paths: list = []
        self.file_status: Dict[str, str] = {}
        self.file_details: Dict[str, dict] = {}
        self.output_path = ctk.StringVar()
        self.interval = ctk.DoubleVar(value=Config.DEFAULT_INTERVAL)
        self.stable_duration = ctk.DoubleVar(value=Config.DEFAULT_STABLE_DURATION)
        self.similarity_threshold = ctk.DoubleVar(value=Config.DEFAULT_SIMILARITY)
        self.output_format = ctk.StringVar(value="pptx")
        self.screenshot_mode = ctk.StringVar(value="interval")
        self.is_converting = False
        self.temp_dir: Optional[str] = None
        self._theme_idx = 0

        # 字体
        self.font_header = ctk.CTkFont(size=16, weight="bold")
        self.font_label = ctk.CTkFont(size=13)
        self.font_small = ctk.CTkFont(size=12)

        # 动画
        self._pulse: Optional[PulseAnimation] = None

        self.create_widgets()

    # ==================== UI 构建 ====================

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        self._build_header(main_frame)
        body = ctk.CTkScrollableFrame(main_frame, fg_color="#f5f5f5", corner_radius=0)
        body.pack(fill="both", expand=True)
        content = ctk.CTkFrame(body, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=32, pady=24)

        self._build_upload_area(content)
        self._build_file_list(content)
        self._build_param_grid(content)
        self._build_screenshot_section(content)
        self._build_progress_section(content)
        self._build_action_bar(content)
        self._update_file_list_visibility()

    def _build_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="#ffffff", height=56, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", padx=28)

        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        ctk.CTkLabel(title_frame, text="▶",
                      font=ctk.CTkFont(size=18, weight="bold"),
                      text_color="#0078d4").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(title_frame, text=Config.WINDOW_TITLE,
                      font=self.font_header,
                      text_color="#000000").pack(side="left", padx=(0, 8))
        ver = ctk.CTkLabel(title_frame, text=f"v{Config.VERSION}",
                            font=ctk.CTkFont(size=10),
                            text_color="#0078d4", fg_color="#e8f0fe",
                            corner_radius=4, padx=8, pady=2)
        ver.pack(side="left")

        # 右侧按钮组
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(side="right", fill="y")

        for btn_cfg in [
            ("📢", lambda: dialogs.show_announcement(self.root)),
            ("🎨", self._cycle_theme),
            ("ⓘ", lambda: dialogs.show_about(self.root)),
        ]:
            ctk.CTkButton(actions, text=btn_cfg[0], width=32, height=32,
                           corner_radius=6, fg_color="transparent",
                           text_color="#000000", hover_color="#f0f0f0",
                           font=ctk.CTkFont(size=14),
                           command=btn_cfg[1]).pack(side="left", padx=4)

    def _build_upload_area(self, parent):
        """上传区域"""
        self.tab_view = ctk.CTkSegmentedButton(
            parent, values=["单个文件", "批量转换"],
            selected_color="#ffffff", selected_hover_color="#ffffff",
            unselected_color="#f0f0f0", unselected_hover_color="#e8e8e8",
            text_color="#000000", command=self.on_tab_change,
            font=self.font_label)
        self.tab_view.pack(anchor="w", pady=(0, 20))
        self.tab_view.set("单个文件")

        upload_frame = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8,
                                     border_width=2, border_color="#d0d0d5")
        upload_frame.pack(fill="x", pady=(0, 16))
        self._upload_frame = upload_frame
        self._pulse = PulseAnimation(upload_frame)

        inner = ctk.CTkFrame(upload_frame, fg_color="transparent")
        inner.pack(fill="both", padx=24, pady=20)
        ctk.CTkLabel(inner, text="📁", font=ctk.CTkFont(size=28),
                      text_color="#000000").pack()
        ctk.CTkLabel(inner, text="点击下方按钮选择视频文件",
                      font=ctk.CTkFont(size=13),
                      text_color="#000000").pack(pady=(4, 2))
        ctk.CTkLabel(inner, text="支持 MP4, AVI, MKV, MOV, WMV, FLV, WEBM 格式",
                      font=ctk.CTkFont(size=11),
                      text_color="#000000").pack()

        self.single_file_label = ctk.CTkLabel(inner, text="",
                                               font=ctk.CTkFont(size=12),
                                               text_color="#0078d4")
        browse_row = ctk.CTkFrame(inner, fg_color="transparent")
        browse_row.pack(pady=(10, 0))
        self.browse_btn = ctk.CTkButton(browse_row, text="浏览文件", width=100, height=30,
                                         fg_color="#0078d4", hover_color="#106ebe",
                                         command=self.select_video,
                                         font=ctk.CTkFont(size=12))
        self.browse_btn.pack(side="left", padx=4)
        self.add_btn = ctk.CTkButton(browse_row, text="添加多个", width=100, height=30,
                                      fg_color="#ffffff", text_color="#000000",
                                      hover_color="#f0f0f0", border_width=1,
                                      border_color="#d0d0d5", command=self.add_videos,
                                      font=ctk.CTkFont(size=12))

    def _build_file_list(self, parent):
        """文件列表"""
        self.file_list_frame = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        self.file_list_inner = ctk.CTkFrame(self.file_list_frame, fg_color="transparent")
        self.file_list_inner.pack(fill="both", padx=8, pady=8)

    def _build_param_grid(self, parent):
        """输出设置 + 去重设置左右并排"""
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 16))

        left = ctk.CTkFrame(grid, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ctk.CTkFrame(grid, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        self._build_output_section(left)
        self._build_dedup_section(right)

    def _build_output_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.pack(fill="x")
        ctk.CTkLabel(section, text="输出设置",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      text_color="#000000").pack(anchor="w", padx=16, pady=(14, 0))

        fmt_frame = ctk.CTkFrame(section, fg_color="transparent")
        fmt_frame.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkLabel(fmt_frame, text="输出格式", font=ctk.CTkFont(size=12),
                      text_color="#000000").pack(anchor="w")
        self.format_segment = ctk.CTkSegmentedButton(
            fmt_frame, values=["PPT (.pptx)", "PDF (.pdf)"],
            selected_color="#ffffff", selected_hover_color="#ffffff",
            unselected_color="#f0f0f0", text_color="#000000",
            command=self._on_format_change, font=ctk.CTkFont(size=12), height=30)
        self.format_segment.pack(fill="x", pady=(6, 0))
        self.format_segment.set("PPT (.pptx)")

        out_frame = ctk.CTkFrame(section, fg_color="transparent")
        out_frame.pack(fill="x", padx=16, pady=(12, 16))
        ctk.CTkLabel(out_frame, text="输出目录", font=ctk.CTkFont(size=12),
                      text_color="#000000").pack(anchor="w")
        row = ctk.CTkFrame(out_frame, fg_color="transparent")
        row.pack(fill="x", pady=(6, 0))
        self.output_entry = ctk.CTkEntry(row, placeholder_text="选择保存位置",
                                          font=ctk.CTkFont(size=12),
                                          height=34, border_width=1,
                                          border_color="#d0d0d5")
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(row, text="浏览", width=60, height=34,
                       fg_color="#f5f5f5", text_color="#000000",
                       hover_color="#e8e8e8", border_width=1,
                       border_color="#d0d0d5",
                       command=self.select_output,
                       font=ctk.CTkFont(size=12)).pack(side="left")

    def _build_dedup_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.pack(fill="x")
        ctk.CTkLabel(section, text="去重设置",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      text_color="#000000").pack(anchor="w", padx=16, pady=(14, 0))

        body = ctk.CTkFrame(section, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(10, 16))

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="去重相似度", font=ctk.CTkFont(size=12),
                      text_color="#000000").pack(side="left")

        entry_frame = ctk.CTkFrame(row, fg_color="transparent")
        entry_frame.pack(side="right")
        self.similarity_entry = ctk.CTkEntry(entry_frame, width=50, height=28,
                                              font=ctk.CTkFont(size=12),
                                              justify="center", border_width=1,
                                              border_color="#d0d0d5")
        self.similarity_entry.pack(side="left")
        self.similarity_entry.insert(0, str(Config.DEFAULT_SIMILARITY))
        ctk.CTkLabel(entry_frame, text="%", font=ctk.CTkFont(size=12),
                      text_color="#000000").pack(side="left", padx=(4, 0))

        self.similarity_slider = ctk.CTkSlider(
            body, from_=Config.SIMILARITY_MIN, to=Config.SIMILARITY_MAX,
            number_of_steps=98, command=self._on_similarity_change,
            height=6, button_corner_radius=14, button_length=28,
            fg_color="#e0e0e0", progress_color="#0078d4",
            button_color="#ffffff", button_hover_color="#f0f0f0", border_width=0)
        self.similarity_slider.pack(fill="x", pady=(8, 0))
        self.similarity_slider.set(Config.DEFAULT_SIMILARITY)

        ctk.CTkLabel(body, text="高于此值视为重复图片",
                      font=ctk.CTkFont(size=10),
                      text_color="#000000").pack(anchor="w", pady=(4, 0))
        self.similarity_entry.bind("<Return>", self._on_similarity_entry_confirm)
        self.similarity_entry.bind("<FocusOut>", self._on_similarity_entry_confirm)

    # ==================== 截图方式 ====================

    def _build_screenshot_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        section.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(section, text="截图方式",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      text_color="#000000").pack(anchor="w", padx=16, pady=(14, 0))

        cards = ctk.CTkFrame(section, fg_color="transparent")
        cards.pack(fill="x", padx=16, pady=(10, 16))

        self.interval_card = OptionCard(
            cards, "定时截图", "⏱", "按固定时间间隔自动截图", self._select_interval_mode)
        self.interval_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # 定时截图参数
        i_body = self.interval_card.card_body
        i_param = ctk.CTkFrame(i_body, fg_color="transparent")
        i_param.pack(fill="x", pady=(6, 0))
        self.interval_entry = ctk.CTkEntry(i_param, textvariable=self.interval,
                                            width=60, height=28,
                                            font=ctk.CTkFont(size=12),
                                            border_width=1, border_color="#d0d0d5",
                                            justify="center")
        self.interval_entry.pack(side="left")
        ctk.CTkLabel(i_param, text="秒 / 张", font=ctk.CTkFont(size=11),
                      text_color="#000000").pack(side="left", padx=(6, 0))

        self.stable_card = OptionCard(
            cards, "静止检测", "▶", "画面静止超过阈值时自动截图", self._select_stable_mode)
        self.stable_card.pack(side="right", fill="both", expand=True, padx=(6, 0))

        s_body = self.stable_card.card_body
        s_param = ctk.CTkFrame(s_body, fg_color="transparent")
        s_param.pack(fill="x", pady=(6, 0))
        self.stable_entry = ctk.CTkEntry(s_param, textvariable=self.stable_duration,
                                          width=60, height=28,
                                          font=ctk.CTkFont(size=12),
                                          border_width=1, border_color="#d0d0d5",
                                          justify="center")
        self.stable_entry.pack(side="left")
        ctk.CTkLabel(s_param, text="秒静止", font=ctk.CTkFont(size=11),
                      text_color="#000000").pack(side="left", padx=(6, 0))

        self._select_interval_mode()

    # ==================== 进度与操作栏 ====================

    def _build_progress_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8)
        frame.pack(fill="x", pady=(0, 16))
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 0))
        ctk.CTkLabel(top, text="进度", font=ctk.CTkFont(size=12),
                      text_color="#000000").pack(side="left")
        self.progress_percent = ctk.CTkLabel(top, text="0%",
                                              font=ctk.CTkFont(size=12, weight="bold"),
                                              text_color="#0078d4")
        self.progress_percent.pack(side="right")
        self.progress_bar = ctk.CTkProgressBar(frame, height=6, corner_radius=3,
                                                fg_color="#e0e0e0",
                                                progress_color="#0078d4")
        self.progress_bar.pack(fill="x", padx=16, pady=(8, 0))
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(frame, text="就绪",
                                          font=ctk.CTkFont(size=12),
                                          text_color="#000000")
        self.status_label.pack(padx=16, pady=(8, 0), anchor="w")
        self.open_folder_btn = ctk.CTkButton(
            frame, text="📂 打开输出文件夹", width=140, height=28,
            fg_color="transparent", text_color="#0078d4",
            hover_color="#e8f0fe", border_width=1, border_color="#0078d4",
            font=ctk.CTkFont(size=11), command=self._open_output_folder)

    def _build_action_bar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(side="right")
        self.cancel_btn = ctk.CTkButton(inner, text="取消", width=90, height=34,
                                         fg_color="transparent",
                                         text_color="#000000",
                                         hover_color="#f0f0f0", border_width=1,
                                         border_color="#d0d0d5",
                                         command=self._on_cancel,
                                         font=ctk.CTkFont(size=13))
        self.cancel_btn.pack(side="left", padx=6)
        self.convert_btn = ctk.CTkButton(inner, text="▶ 开始转换", width=120, height=34,
                                          fg_color="#0078d4", hover_color="#106ebe",
                                          command=self.start_conversion,
                                          font=ctk.CTkFont(size=13, weight="bold"))
        self.convert_btn.pack(side="left", padx=6)

    # ==================== 模式切换 ====================

    def _select_interval_mode(self):
        self.screenshot_mode.set("interval")
        self.interval_card.set_selected(True)
        self.stable_card.set_selected(False)
        try:
            self.interval_entry.configure(border_color="#0078d4")
            self.stable_entry.configure(border_color="#d0d0d5")
        except Exception:
            pass

    def _select_stable_mode(self):
        self.screenshot_mode.set("stable")
        self.stable_card.set_selected(True)
        self.interval_card.set_selected(False)
        try:
            self.stable_entry.configure(border_color="#0078d4")
            self.interval_entry.configure(border_color="#d0d0d5")
        except Exception:
            pass

    def _on_format_change(self, value):
        self.output_format.set("pptx" if "PPT" in value else "pdf")

    def _on_similarity_change(self, value):
        val = round(value)
        self.similarity_threshold.set(val)
        self.similarity_entry.delete(0, "end")
        self.similarity_entry.insert(0, str(val))

    def _on_similarity_entry_confirm(self, event=None):
        try:
            val = int(self.similarity_entry.get())
            val = max(int(Config.SIMILARITY_MIN), min(int(Config.SIMILARITY_MAX), val))
            self.similarity_threshold.set(val)
            self.similarity_slider.set(val)
            self.similarity_entry.delete(0, "end")
            self.similarity_entry.insert(0, str(val))
        except ValueError:
            self.similarity_entry.delete(0, "end")
            self.similarity_entry.insert(0, str(int(self.similarity_threshold.get())))

    def on_tab_change(self, value):
        if value == "批量转换":
            self.browse_btn.pack_forget()
            self.add_btn.pack(side="left", padx=4)
            self.single_file_label.pack_forget()
        else:
            self.add_btn.pack_forget()
            self.browse_btn.pack(side="left", padx=4)
            self.file_list_frame.pack_forget()
            self.single_file_label.pack_forget()
        self._update_file_list_visibility()

    # ==================== 主题 ====================

    def _cycle_theme(self):
        self._theme_idx = (self._theme_idx + 1) % len(THEMES)
        self.root.config(cursor="watch")
        self._apply_theme()
        self.root.config(cursor="")

    def _apply_theme(self):
        t = THEMES[self._theme_idx]
        if ctk.get_appearance_mode() != t["mode"]:
            ctk.set_appearance_mode(t["mode"])

        self.progress_bar.configure(progress_color=t["progress"])
        self.similarity_slider.configure(progress_color=t["progress"])
        self.progress_percent.configure(text_color=t["accent"])
        self.convert_btn.configure(fg_color=t["accent"], hover_color=t["accent_hover"])
        self.open_folder_btn.configure(text_color=t["accent"], border_color=t["accent"],
                                        hover_color=t["accent_bg"])
        for card in (self.interval_card, self.stable_card):
            card.select_badge.configure(fg_color=t["accent"], hover_color=t["accent_hover"])

    # ==================== 文件选择 ====================

    def select_video(self):
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", " ".join(f"*{e}" for e in Config.SUPPORTED_VIDEO_EXTS)),
                       ("所有文件", "*.*")])
        if file_path and is_valid_video_file(file_path):
            self.video_paths = [file_path]
            self.file_status = {file_path: "pending"}
            self.file_details = {}
            self.single_file_label.pack(pady=(8, 0))
            self.single_file_label.configure(text=f"已选择: {Path(file_path).name}")
            if not self.output_path.get():
                d = str(Path(file_path).parent)
                self.output_path.set(d)
                self._set_output_entry(d)
        elif file_path:
            messagebox.showerror("错误", f"'{Path(file_path).name}' 不是有效的视频文件。")

    def add_videos(self):
        file_paths = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[("视频文件", " ".join(f"*{e}" for e in Config.SUPPORTED_VIDEO_EXTS)),
                       ("所有文件", "*.*")])
        if not file_paths:
            return
        added = 0
        for fp in file_paths:
            if fp not in self.video_paths and is_valid_video_file(fp):
                self.video_paths.append(fp)
                self.file_status[fp] = "pending"
                added += 1
        if added > 0:
            self._update_file_list_visibility()
            if not self.output_path.get():
                self.output_path.set(str(Path(self.video_paths[0]).parent))
                self._set_output_entry(self.output_path.get())

    def _set_output_entry(self, text: str):
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, text)

    def select_output(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.output_path.set(d)
            self._set_output_entry(d)

    def _update_file_list_visibility(self):
        for w in self.file_list_inner.winfo_children():
            w.destroy()

        if not self.video_paths:
            self.file_list_frame.pack_forget()
            if self._pulse:
                self._pulse.start()
            return

        self.file_list_frame.pack(fill="x", pady=(0, 16))
        if self._pulse:
            self._pulse.stop()

        status_icons = {
            "pending": ("⏳", "#888888"),
            "processing": ("⏳", "#0078d4"),
            "completed": ("✅", "#00b894"),
            "failed": ("❌", "#d63031"),
        }

        for idx, fp in enumerate(self.video_paths):
            p = Path(fp)
            status = self.file_status.get(fp, "pending")
            row = ctk.CTkFrame(self.file_list_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=str(idx + 1), width=24,
                          font=ctk.CTkFont(size=11),
                          text_color="#888888").pack(side="left")
            ctk.CTkLabel(row, text=p.name, font=ctk.CTkFont(size=12),
                          text_color="#000000", anchor="w").pack(
                              side="left", fill="x", expand=True, padx=(4, 4))
            ctk.CTkLabel(row, text=format_file_size(p.stat().st_size),
                          width=70, font=ctk.CTkFont(size=10),
                          text_color="#888888").pack(side="left")
            icon, color = status_icons.get(status, ("⏳", "#888888"))
            ctk.CTkLabel(row, text=icon, width=24,
                          font=ctk.CTkFont(size=11),
                          text_color=color).pack(side="left")
            ctk.CTkButton(row, text="✕", width=24, height=22, corner_radius=4,
                           fg_color="transparent", text_color="#cc0000",
                           hover_color="#ffe0e0", font=ctk.CTkFont(size=11),
                           command=lambda i=idx: self._remove_file_row(i)).pack(
                               side="left", padx=(2, 0))

    def _remove_file_row(self, index: int):
        if 0 <= index < len(self.video_paths):
            fp = self.video_paths.pop(index)
            self.file_status.pop(fp, None)
            self.file_details.pop(fp, None)
            self._update_file_list_visibility()

    # ==================== 转换控制 ====================

    def start_conversion(self):
        missing = check_dependencies()
        if missing:
            messagebox.showerror("缺少依赖",
                f"缺少必要的 Python 库: {', '.join(missing)}\n\n"
                f"请运行:\npip install {' '.join(missing)}")
            return

        if self.tab_view.get() == "单个文件":
            if not self.video_paths:
                messagebox.showerror("错误", "请先选择视频文件!")
                return
            for fp in self.video_paths:
                if not os.path.exists(fp):
                    messagebox.showerror("错误", f"文件不存在:\n{fp}")
                    return
        elif not self.video_paths:
            messagebox.showerror("错误", "请先添加视频文件!")
            return

        output_dir = self.output_entry.get()
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录!")
            return
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录:\n{e}")
                return

        if self.is_converting:
            messagebox.showwarning("警告", "转换正在进行中...")
            return

        self.temp_dir = tempfile.mkdtemp(prefix="video2ppt_")
        self.is_converting = True
        self.convert_btn.configure(state="disabled")
        self.cancel_btn.configure(text="取消转换", state="normal")
        self.open_folder_btn.pack_forget()
        self.update_status("正在处理视频...")

        callbacks = {
            'on_status': lambda msg: self.update_status(msg),
            'on_progress': lambda pct: self.update_progress(pct),
            'on_file_status': lambda path, st: self._set_file_status(path, st),
            'on_file_detail': lambda path, det: self.file_details.update({path: det}),
            'should_cancel': lambda: not self.is_converting,
        }

        engine = VideoEngine(
            screenshot_mode=self.screenshot_mode.get(),
            interval=self.interval.get(),
            stable_duration=self.stable_duration.get(),
            similarity_threshold=self.similarity_threshold.get(),
        )
        task = ConversionTask(
            video_paths=list(self.video_paths),
            output_dir=output_dir,
            format_ext=self.output_format.get(),
            engine=engine,
            callbacks=callbacks,
        )

        thread = threading.Thread(target=self._run_task, args=(task,), daemon=True)
        thread.start()

    def _run_task(self, task: ConversionTask):
        """在线程中执行转换任务"""
        try:
            success_count, fail_count, results = task.run(self.temp_dir)
            if self.is_converting:
                self.root.after(0, lambda: dialogs.show_result(
                    self.root, success_count, fail_count, results,
                    self._open_output_folder))
                self.root.after(0, lambda: self.open_folder_btn.pack(
                    padx=16, pady=(4, 12), anchor="w"))
        except Exception as e:
            self.root.after(0, lambda: self.update_status(f"错误: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换失败:\n{str(e)}"))
        finally:
            self.is_converting = False
            self.root.after(0, lambda: self.convert_btn.configure(state="normal"))
            self.root.after(0, lambda: self.cancel_btn.configure(text="取消", state="normal"))

    def _set_file_status(self, path: str, status: str):
        self.file_status[path] = status
        self.root.after(0, self._update_file_list_visibility)

    # ==================== UI 更新 ====================

    def update_progress(self, value: float):
        self.root.after(0, lambda: self.progress_bar.set(value / 100))
        self.root.after(0, lambda: self.progress_percent.configure(text=f"{value:.0f}%"))

    def update_status(self, message: str):
        self.root.after(0, lambda: self.status_label.configure(text=message))

    # ==================== 窗口管理 ====================

    def _on_cancel(self):
        if self.is_converting:
            if messagebox.askyesno("取消转换", "确定要取消正在进行的转换吗？"):
                self.is_converting = False
                self.cancel_btn.configure(state="disabled", text="正在取消…")
        else:
            self.on_close()

    def _open_output_folder(self):
        path = self.output_entry.get()
        if path and os.path.exists(path):
            subprocess.Popen(f'explorer "{os.path.normpath(path)}"')

    def on_close(self):
        if self.is_converting:
            if messagebox.askyesno("退出警告", "转换正在进行中，确定要退出吗？\n未完成的转换将被中断"):
                self.root.destroy()
        else:
            self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._apply_theme()
        self.root.after(500, lambda: dialogs.show_announcement(self.root))
        if self._pulse:
            self._pulse.start()
        self.root.mainloop()
