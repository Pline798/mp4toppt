"""可复用的 UI 组件"""

from typing import Callable, Optional
import customtkinter as ctk

from config import Config


class OptionCard(ctk.CTkFrame):
    """可点击的选项卡片，支持选中状态标识"""

    def __init__(self, parent, title: str, icon: str, desc: str,
                 on_select: Callable, **kwargs):
        super().__init__(parent, fg_color="#f9f9fb", corner_radius=8,
                         border_width=1, border_color="#e0e0e4", **kwargs)
        self._on_select = on_select
        self._selected = False

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", padx=14, pady=12)

        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(title_row, text=f"{icon} {title}",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      text_color="#000000").pack(side="left")

        self.select_badge = ctk.CTkButton(
            title_row, text="已选", width=48, height=22, corner_radius=11,
            fg_color="#0078d4", text_color="#ffffff", hover_color="#0078d4",
            font=ctk.CTkFont(size=11, weight="bold")
        )

        ctk.CTkLabel(inner, text=desc, font=ctk.CTkFont(size=11),
                      text_color="#000000").pack(anchor="w", pady=(2, 0))

        self.card_body = inner

        # 卡片整体可点击
        self._bind_click_recursive(self)

    def _bind_click_recursive(self, widget):
        widget.bind("<Button-1>", lambda e: self._on_select(), add="+")
        for child in widget.winfo_children():
            self._bind_click_recursive(child)

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.configure(border_color="#0078d4", fg_color="#f0f7ff")
            self.select_badge.pack(side="right", padx=(8, 0))
        else:
            self.configure(border_color="#e0e0e4", fg_color="#f9f9fb")
            self.select_badge.pack_forget()


class PulseAnimation:
    """上传区域边框呼吸动画"""

    def __init__(self, frame):
        self._frame = frame
        self._running = False
        self._timer_id: Optional[str] = None

    def start(self):
        self._running = True
        self._step(0)

    def stop(self):
        self._running = False
        self._timer_id = None
        try:
            self._frame.configure(border_color="#d0d0d5")
        except Exception:
            pass

    def _step(self, step: int):
        if not self._running:
            return
        colors = ["#d0d0d5", "#c5c8d8", "#b8bddb", "#aab2de",
                   "#b8bddb", "#c5c8d8"]
        try:
            self._frame.configure(border_color=colors[step % len(colors)])
        except Exception:
            pass
        try:
            root = self._frame.winfo_toplevel()
            self._timer_id = root.after(800, lambda: self._step(step + 1))
        except Exception:
            pass
