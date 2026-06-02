"""对话框窗口 - 统一管理淡入淡出动画"""

from typing import Callable, List, Optional, Tuple
import customtkinter as ctk
from config import Config


def _fade_in(dialog: ctk.CTkToplevel, steps: int = 10, interval: int = 25,
             on_done: Optional[Callable] = None):
    """淡入动画"""
    def _tick(step: int = 0):
        alpha = step / steps
        try:
            dialog.attributes("-alpha", alpha)
        except Exception:
            pass
        if step < steps:
            dialog.after(interval, lambda: _tick(step + 1))
        else:
            dialog.attributes("-topmost", False)
            if on_done:
                on_done()
    _tick()


def _fade_out(dialog: ctk.CTkToplevel, steps: int = 10, interval: int = 25,
              on_done: Optional[Callable] = None):
    """淡出动画并销毁"""
    def _tick(step: int = steps):
        alpha = step / steps
        try:
            dialog.attributes("-alpha", alpha)
        except Exception:
            pass
        if step > 0:
            dialog.after(interval, lambda: _tick(step - 1))
        else:
            try:
                dialog.grab_release()
            except Exception:
                pass
            try:
                dialog.destroy()
            except Exception:
                pass
            if on_done:
                on_done()
    _tick()


def _center_on_parent(dialog: ctk.CTkToplevel, parent, w: int, h: int):
    """将弹窗居中于父窗口"""
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - w) // 2
    y = parent.winfo_y() + (parent.winfo_height() - h) // 2
    dialog.geometry(f"+{x}+{y}")


def _setup_dialog(parent, title: str, width: int, height: int) -> ctk.CTkToplevel:
    """创建并初始化弹窗"""
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry(f"{width}x{height}")
    dialog.resizable(False, False)
    dialog.attributes("-alpha", 0.0)
    dialog.transient(parent)
    dialog.lift()
    dialog.attributes("-topmost", True)
    _center_on_parent(dialog, parent, width, height)

    frame = ctk.CTkFrame(dialog, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)
    return dialog


def show_about(parent):
    """关于弹窗"""
    dialog = _setup_dialog(parent, "关于", 420, 320)
    frame = list(dialog.winfo_children())[0]

    ctk.CTkLabel(frame, text="ⓘ 关于",
                 font=ctk.CTkFont(size=18, weight="bold"),
                 text_color="#000000").pack(anchor="w", pady=(0, 12))

    content = (
        "视频转 PPT/PDF 工具 v1.0\n\n"
        "将视频文件批量转换为 PPT 或 PDF 文档。\n\n"
        "技术栈:\n"
        "  Python + CustomTkinter + OpenCV\n\n"
        "支持格式:\n"
        "  MP4 / AVI / MKV / MOV / WMV / FLV / WEBM\n\n"
        "v1.0 改进:\n"
        "  ✅ 修复静止检测时长偏差 Bug\n"
        "  ✅ 帧哈希缓存提升性能\n"
        "  ✅ 架构拆分，代码更易维护\n\n"
        "© 2026 视频转 PPT/PDF Tool"
    )
    tb = ctk.CTkTextbox(frame, wrap="word", font=ctk.CTkFont(size=13),
                         fg_color="#f9f9fb", text_color="#000000",
                         border_width=1, border_color="#e0e0e4", corner_radius=6)
    tb.pack(fill="both", expand=True, pady=(0, 16))
    tb.insert("0.0", content)
    tb.configure(state="disabled")

    ctk.CTkButton(frame, text="关闭", width=100, height=34,
                   fg_color="#0078d4", hover_color="#106ebe",
                   command=lambda: _fade_out(dialog),
                   font=ctk.CTkFont(size=13, weight="bold")).pack()

    _fade_in(dialog, on_done=lambda: dialog.grab_set())


def show_announcement(parent):
    """更新公告弹窗"""
    dialog = _setup_dialog(parent, "更新公告", 500, 420)
    frame = list(dialog.winfo_children())[0]

    ctk.CTkLabel(frame, text="🎉 v1.0 更新公告",
                 font=ctk.CTkFont(size=18, weight="bold"),
                 text_color="#000000").pack(anchor="w", pady=(0, 12))

    content = (
        "感谢您使用视频转 PPT/PDF 工具！\n\n"
        "v1.0 主要更新内容：\n"
        "  🐛 修复静止检测模式 Bug\n"
        "     - 实际所需时长是用户设定值数倍的问题\n\n"
        "  ⚡ 性能优化\n"
        "     - 帧间对比缓存哈希，减少 50% 重复计算\n\n"
        "  🏗 架构重构\n"
        "     - main.py 拆分为 app/dialogs/widgets 模块\n"
        "     - 集中式 Config 管理，消除魔术数字\n"
        "     - 完整的类型提示\n\n"
        "  🛡 健壮性提升\n"
        "     - 完整的依赖检查（含 OpenCV）\n"
        "     - 改进的临时目录清理逻辑\n\n"
        "如有问题或建议，欢迎反馈！"
    )
    tb = ctk.CTkTextbox(frame, wrap="word", font=ctk.CTkFont(size=13),
                         fg_color="#f9f9fb", text_color="#000000",
                         border_width=1, border_color="#e0e0e4", corner_radius=6)
    tb.pack(fill="both", expand=True, pady=(0, 16))
    tb.insert("0.0", content)
    tb.configure(state="disabled")

    ctk.CTkButton(frame, text="我知道了", width=120, height=34,
                   fg_color="#0078d4", hover_color="#106ebe",
                   command=lambda: _fade_out(dialog),
                   font=ctk.CTkFont(size=13, weight="bold")).pack()

    _fade_in(dialog, on_done=lambda: dialog.grab_set())


def show_result(parent, success_count: int, fail_count: int,
                results: List[Tuple[str, str]], on_open_folder: Callable):
    """转换结果弹窗"""
    dialog = _setup_dialog(parent, "转换完成", 420, 380)
    frame = list(dialog.winfo_children())[0]

    ctk.CTkLabel(frame, text="转换结果",
                 font=ctk.CTkFont(size=16, weight="bold"),
                 text_color="#000000").pack(anchor="w")

    # 概要
    bg_color = "#f0faf0" if fail_count == 0 else "#fff8f0"
    summary = ctk.CTkFrame(frame, fg_color=bg_color, corner_radius=6)
    summary.pack(fill="x", pady=(10, 12))
    txt = f"✅ 成功: {success_count} 个"
    if fail_count > 0:
        txt += f"   ❌ 失败: {fail_count} 个"
    ctk.CTkLabel(summary, text=txt,
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color="#000000").pack(padx=16, pady=12)

    # 详情
    ctk.CTkLabel(frame, text="文件处理详情:",
                 font=ctk.CTkFont(size=12, weight="bold"),
                 text_color="#000000").pack(anchor="w")
    tb = ctk.CTkTextbox(frame, height=120, wrap="word",
                         font=ctk.CTkFont(size=12),
                         fg_color="#f9f9fb", text_color="#000000",
                         border_width=1, border_color="#e0e0e4", corner_radius=6)
    tb.pack(fill="x", pady=(4, 12))
    for name, detail in results:
        tb.insert("end", f"  {detail}  {name}\n")
    tb.configure(state="disabled")

    # 按钮
    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.pack(fill="x")
    ctk.CTkButton(btn_frame, text="📂 打开文件夹", width=130, height=34,
                   fg_color="transparent", text_color="#0078d4",
                   hover_color="#e8f0fe", border_width=1, border_color="#0078d4",
                   font=ctk.CTkFont(size=12),
                   command=lambda: [on_open_folder(), _fade_out(dialog)]).pack(
                       side="left", padx=(0, 8))
    ctk.CTkButton(btn_frame, text="关闭", width=90, height=34,
                   fg_color="#0078d4", hover_color="#106ebe",
                   font=ctk.CTkFont(size=12),
                   command=lambda: _fade_out(dialog)).pack(side="right")

    _fade_in(dialog, on_done=lambda: dialog.grab_set())
