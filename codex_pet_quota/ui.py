import ctypes
import datetime as dt
import math
import os
import queue
import threading
import time
import tkinter as tk
from typing import Optional

from .models import AlertDecision, PetTarget, WeeklyQuotaView
from .pet_locator import PetLocator, cursor_state
from .service import QuotaService


WHITE = "#ffffff"
TEXT = "#202124"
MUTED = "#6b7280"
GREEN = "#10b981"
WARNING = "#f59e0b"
PILL_WIDTH = 248
PILL_HEIGHT = 48
HOVER_TRIGGER_SECONDS = 0.10
DISMISS_DELAY_SECONDS = 0.35
IDLE_TICK_MS = 50
DRAG_TICK_MS = 16
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
GWL_EXSTYLE = -20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2


def format_reset_relative(resets_at: int, now: Optional[dt.datetime] = None) -> str:
    reset = dt.datetime.fromtimestamp(resets_at).astimezone()
    current = now or dt.datetime.now().astimezone()
    seconds = (reset - current).total_seconds()
    if seconds <= 0:
        return "即将重置"
    if seconds < 86400:
        return "今天重置"
    return "%d天后重置" % int(math.ceil(seconds / 86400.0))


def translate_target(target: PetTarget, dx: int, dy: int) -> PetTarget:
    left, top, right, bottom = target.rect
    return PetTarget(
        hwnd=target.hwnd,
        process_id=target.process_id,
        rect=(left + dx, top + dy, right + dx, bottom + dy),
        score=target.score,
        class_name=target.class_name,
        confidence="cursor-drag-follow",
    )


class QuotaWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Codex 周额度")
        self.root.configure(bg=WHITE)
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.resizable(False, False)
        self.root.withdraw()
        self.locator = PetLocator()
        self.target = None  # type: Optional[PetTarget]
        self.service = QuotaService()
        self.result_queue = queue.Queue()
        self.fetching = False
        self.last_refresh = 0.0
        self.last_view = None  # type: Optional[WeeklyQuotaView]
        self.active_until = 0.0
        self.hover_since = None  # type: Optional[float]
        self.drag_active = False
        self.drag_origin_cursor = None  # type: Optional[tuple]
        self.drag_origin_target = None  # type: Optional[PetTarget]
        self.quota_text = tk.StringVar(value="周额度")
        self.reset_text = tk.StringVar(value="等待宠物交互")
        self._build()
        self.root.update_idletasks()
        self._apply_window_style()
        self.root.after(IDLE_TICK_MS, self._tick)

    def _build(self):
        outer = tk.Frame(
            self.root,
            bg=WHITE,
            padx=14,
            pady=8,
            highlightbackground="#eceff3",
            highlightthickness=1,
        )
        outer.pack(fill="both", expand=True)
        self.dot = tk.Label(outer, text="●", bg=WHITE, fg=GREEN, font=("Segoe UI", 8))
        self.dot.pack(side="left", padx=(0, 7))
        tk.Label(
            outer,
            textvariable=self.quota_text,
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI Variable Text", 10, "bold"),
        ).pack(side="left")
        tk.Frame(outer, bg="#e5e7eb", width=1, height=20).pack(side="left", padx=10)
        tk.Label(
            outer,
            textvariable=self.reset_text,
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI Variable Text", 9),
        ).pack(side="left")

    def _apply_window_style(self):
        if os.name != "nt":
            return
        hwnd = self.root.winfo_id()
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            style | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        )
        try:
            preference = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except Exception:
            pass
        region = gdi32.CreateRoundRectRgn(0, 0, PILL_WIDTH + 1, PILL_HEIGHT + 1, 24, 24)
        user32.SetWindowRgn(hwnd, region, True)

    def _place_near_target(self, target: PetTarget):
        left, top, right, bottom = target.rect
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        center = (left + right) // 2
        x = max(8, min(screen_w - PILL_WIDTH - 8, center - PILL_WIDTH // 2))
        y = top - PILL_HEIGHT - 10
        if y < 8:
            y = min(screen_h - PILL_HEIGHT - 48, bottom + 12)
        self.root.geometry("%dx%d+%d+%d" % (PILL_WIDTH, PILL_HEIGHT, x, y))

    def _show_loading(self):
        self.dot.configure(fg="#9ca3af")
        self.quota_text.set("周额度")
        self.reset_text.set("正在读取…")

    def refresh_for_interaction(self):
        if self.fetching or (self.last_refresh > 0 and time.time() - self.last_refresh < 30):
            return
        self.fetching = True
        self._show_loading()

        def work():
            try:
                self.result_queue.put(("ok",) + self.service.refresh())
            except Exception as exc:
                self.result_queue.put(("error", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _render(self, view: WeeklyQuotaView, decision: AlertDecision):
        self.last_view = view
        if not view.is_ready:
            self.dot.configure(fg="#9ca3af")
            self.quota_text.set("周额度暂不可用")
            self.reset_text.set(view.message or "请稍后重试")
            return
        remaining = float(view.remaining_percent)
        shown = ("%.1f" % remaining).rstrip("0").rstrip(".") + "%"
        self.dot.configure(fg=WARNING if remaining < 20 else GREEN)
        self.quota_text.set("周剩余 %s" % shown)
        if view.resets_at:
            self.reset_text.set(format_reset_relative(view.resets_at))
        else:
            self.reset_text.set("重置时间未知")
    def _on_interaction(self, target: PetTarget):
        self.target = target
        self._place_near_target(target)
        self.active_until = max(
            self.active_until, time.monotonic() + DISMISS_DELAY_SECONDS
        )
        if self.last_view is not None:
            cached_low = (
                self.last_view.remaining_percent is not None
                and self.last_view.remaining_percent < 20
            )
            self._render(self.last_view, AlertDecision(False, cached_low, "cached"))
        else:
            self._show_loading()
        self.root.deiconify()
        self.refresh_for_interaction()

    def _interaction_tick(self):
        now = time.monotonic()
        x, y, left_down = cursor_state()

        # Electron currently persists the final pet position after a drag, not
        # every intermediate frame. Follow the mouse delta directly at ~60 FPS
        # while the left button is held, then return to the official state.
        if self.drag_active and left_down and self.drag_origin_target is not None:
            origin_x, origin_y = self.drag_origin_cursor
            predicted = translate_target(
                self.drag_origin_target, x - origin_x, y - origin_y
            )
            self._on_interaction(predicted)
            return

        if self.drag_active and not left_down:
            self.drag_active = False
            self.drag_origin_cursor = None
            self.drag_origin_target = None
            self.active_until = max(
                self.active_until, now + DISMISS_DELAY_SECONDS
            )

        target = self.locator.locate()
        if target is not None:
            if left_down:
                self.drag_active = True
                self.drag_origin_cursor = (x, y)
                self.drag_origin_target = target
                self._on_interaction(target)
                self.hover_since = now
            else:
                if self.hover_since is None:
                    self.hover_since = now
                if now - self.hover_since >= HOVER_TRIGGER_SECONDS:
                    self._on_interaction(target)
        else:
            self.hover_since = None
        if now >= self.active_until:
            self.root.withdraw()

    def _tick(self):
        try:
            while True:
                item = self.result_queue.get_nowait()
                self.fetching = False
                self.last_refresh = time.time()
                if item[0] == "ok":
                    self._render(item[1], item[2])
                else:
                    self.dot.configure(fg="#9ca3af")
                    self.quota_text.set("周额度读取失败")
                    self.reset_text.set("下次交互重试")
        except queue.Empty:
            pass
        self._interaction_tick()
        self.root.after(DRAG_TICK_MS if self.drag_active else IDLE_TICK_MS, self._tick)

    def close(self):
        self.service.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
