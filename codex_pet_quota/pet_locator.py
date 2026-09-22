import ctypes
import json
import os
import time
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .models import PetTarget


if os.name == "nt":
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32
    dwmapi = ctypes.windll.dwmapi
    handle_type = ctypes.c_void_p
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = handle_type
    user32.ReleaseDC.argtypes = [wintypes.HWND, handle_type]
    gdi32.CreateCompatibleDC.argtypes = [handle_type]
    gdi32.CreateCompatibleDC.restype = handle_type
    gdi32.CreateCompatibleBitmap.argtypes = [handle_type, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = handle_type
    gdi32.SelectObject.argtypes = [handle_type, handle_type]
    gdi32.SelectObject.restype = handle_type
    gdi32.BitBlt.argtypes = [
        handle_type,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        handle_type,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.DWORD,
    ]
    gdi32.BitBlt.restype = wintypes.BOOL
    gdi32.GetDIBits.argtypes = [
        handle_type,
        handle_type,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.UINT,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [handle_type]
    gdi32.DeleteDC.argtypes = [handle_type]
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass
else:
    user32 = gdi32 = kernel32 = dwmapi = None


GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DWMWA_CLOAKED = 14
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0
PET_SAMPLE_SIZE = 112
DEFAULT_OVERLAY_WIDTH = 110.0
DEFAULT_OVERLAY_HEIGHT = 110.0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


@dataclass(frozen=True)
class WindowDiagnostic:
    hwnd: int
    process_id: int
    rect: Tuple[int, int, int, int]
    visible: bool
    cloaked: bool
    class_name: str
    title: str
    image_name: str
    ex_style: int
    score: int


def _text(hwnd: int, class_name: bool = False) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    if class_name:
        user32.GetClassNameW(hwnd, buffer, len(buffer))
    else:
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def _image_name(process_id: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _is_codex_image(path: str) -> bool:
    lowered = path.lower().replace("/", "\\")
    return (
        "\\openai.codex_" in lowered
        or "\\openai\\codex\\" in lowered
        or lowered.endswith("\\chatgpt.exe")
    )


def enumerate_codex_windows() -> List[WindowDiagnostic]:
    if os.name != "nt":
        return []
    values = []  # type: List[WindowDiagnostic]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _lparam):
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        image = _image_name(process_id.value)
        if not _is_codex_image(image):
            return True
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        visible = bool(user32.IsWindowVisible(hwnd))
        cloaked_value = wintypes.DWORD()
        cloaked = False
        try:
            if dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked_value), ctypes.sizeof(cloaked_value)
            ) == 0:
                cloaked = bool(cloaked_value.value)
        except Exception:
            pass
        title = _text(hwnd)
        cls = _text(hwnd, class_name=True)
        ex_style = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        score = 3
        score += 2 if not title else 0
        score += 2 if ex_style & WS_EX_LAYERED else 0
        score += 2 if ex_style & WS_EX_TOOLWINDOW else 0
        score += 1 if ex_style & WS_EX_TOPMOST else 0
        score += 2 if 32 <= width <= 640 and 32 <= height <= 640 else -3
        score += 1 if visible and not cloaked else -4
        values.append(
            WindowDiagnostic(
                hwnd=int(hwnd),
                process_id=int(process_id.value),
                rect=(rect.left, rect.top, rect.right, rect.bottom),
                visible=visible,
                cloaked=cloaked,
                class_name=cls,
                title=title[:80],
                image_name=os.path.basename(image),
                ex_style=ex_style,
                score=score,
            )
        )
        return True

    user32.EnumWindows(callback_type(visit), 0)
    return sorted(values, key=lambda item: item.score, reverse=True)


def classify_pet_pixels(pixels: Sequence[Tuple[int, int, int]]) -> Tuple[bool, Dict[str, float]]:
    """Classify a cursor-centered patch without retaining the image."""
    count = len(pixels)
    if count == 0:
        return False, {"score": 0.0}
    near_white = 0
    dark = 0
    colorful = 0
    warm_outline = 0
    cool_accent = 0
    for red, green, blue in pixels:
        maximum = max(red, green, blue)
        minimum = min(red, green, blue)
        if red >= 220 and green >= 220 and blue >= 220:
            near_white += 1
        if red + green + blue < 390:
            dark += 1
        if maximum - minimum >= 28 and maximum < 248:
            colorful += 1
        if 55 <= red <= 185 and 25 <= green <= 135 and 15 <= blue <= 120 and red >= green + 15:
            warm_outline += 1
        if blue >= red + 18 and blue >= green + 8 and blue >= 75:
            cool_accent += 1
    ratios = {
        "whiteRatio": near_white / count,
        "darkRatio": dark / count,
        "colorRatio": colorful / count,
        "warmRatio": warm_outline / count,
        "coolRatio": cool_accent / count,
    }
    score = 0.0
    # The current pet has a white body, a strong warm outline and a small blue
    # accent. Its normal background can be dark purple; a right-click menu is
    # mostly white and must not become a false positive.
    score += 2.0 if 0.18 <= ratios["whiteRatio"] <= 0.85 else 0.0
    score += 2.0 if 0.03 <= ratios["darkRatio"] <= 0.75 else 0.0
    score += 2.0 if 0.05 <= ratios["colorRatio"] <= 0.75 else 0.0
    score += 3.0 if ratios["warmRatio"] >= 0.04 else 0.0
    score += 1.0 if 0.001 <= ratios["coolRatio"] <= 0.12 else 0.0
    ratios["score"] = score
    return score >= 8.0, ratios


def _capture_patch(left: int, top: int, width: int, height: int) -> Sequence[Tuple[int, int, int]]:
    screen_dc = user32.GetDC(0)
    memory_dc = gdi32.CreateCompatibleDC(screen_dc)
    bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    old_object = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if not gdi32.BitBlt(memory_dc, 0, 0, width, height, screen_dc, left, top, SRCCOPY):
            return []
        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        buffer = (ctypes.c_ubyte * (width * height * 4))()
        rows = gdi32.GetDIBits(memory_dc, bitmap, 0, height, buffer, ctypes.byref(info), DIB_RGB_COLORS)
        if rows != height:
            return []
        return [(buffer[index + 2], buffer[index + 1], buffer[index]) for index in range(0, len(buffer), 4)]
    finally:
        gdi32.SelectObject(memory_dc, old_object)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(0, screen_dc)


def cursor_state() -> Tuple[int, int, bool]:
    if os.name != "nt":
        return 0, 0, False
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    left_down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
    return point.x, point.y, left_down


def _official_pet_state_path() -> Path:
    override = os.environ.get("CODEX_PET_STATE_FILE")
    if override:
        return Path(override)
    return Path.home() / ".codex" / ".codex-global-state.json"


def _screen_scale() -> float:
    """Convert Electron/WPF logical desktop coordinates to physical pixels."""
    if os.name != "nt":
        return 1.0
    try:
        return max(0.5, min(4.0, float(user32.GetDpiForSystem()) / 96.0))
    except Exception:
        return 1.0


def parse_official_pet_state(payload: object, scale: float = 1.0) -> Optional[PetTarget]:
    """Read the pet rectangle persisted by the official Codex desktop client.

    Older clients stored a nested ``mascot`` rectangle. Current clients persist
    the overlay origin only; the official overlay is 110 logical pixels square.
    """
    if not isinstance(payload, dict):
        return None
    pet_state = payload
    if "electron-avatar-overlay-bounds" not in pet_state:
        persisted = payload.get("electron-persisted-atom-state")
        if isinstance(persisted, str):
            try:
                persisted = json.loads(persisted)
            except (TypeError, ValueError):
                return None
        if isinstance(persisted, dict):
            pet_state = persisted
    if pet_state.get("electron-avatar-overlay-open") is not True:
        return None
    bounds = pet_state.get("electron-avatar-overlay-bounds")
    if not isinstance(bounds, dict):
        return None
    try:
        x = float(bounds["x"])
        y = float(bounds["y"])
        mascot = bounds.get("mascot")
        if isinstance(mascot, dict):
            x += float(mascot.get("left", 0.0))
            y += float(mascot.get("top", 0.0))
            width = float(mascot.get("width", DEFAULT_OVERLAY_WIDTH))
            height = float(mascot.get("height", DEFAULT_OVERLAY_HEIGHT))
            confidence = "official-state-mascot"
        else:
            width = float(bounds.get("width", DEFAULT_OVERLAY_WIDTH))
            height = float(bounds.get("height", DEFAULT_OVERLAY_HEIGHT))
            confidence = "official-state-overlay"
    except (KeyError, TypeError, ValueError):
        return None
    left = int(round(x * scale))
    top = int(round(y * scale))
    right = int(round((x + width) * scale))
    bottom = int(round((y + height) * scale))
    if right <= left or bottom <= top:
        return None
    return PetTarget(
        hwnd=0,
        process_id=0,
        rect=(left, top, right, bottom),
        score=100,
        class_name="CodexOfficialPetState",
        confidence=confidence,
    )


def read_official_pet_target(path: Optional[Path] = None) -> Optional[PetTarget]:
    state_path = path or _official_pet_state_path()
    try:
        with state_path.open("r", encoding="utf-8-sig") as stream:
            payload = json.load(stream)
        return parse_official_pet_state(payload, _screen_scale())
    except (OSError, TypeError, ValueError):
        return None


class PetLocator:
    def __init__(self):
        self._windows = []  # type: List[WindowDiagnostic]
        self._last_window_scan = 0.0
        self._official_path = _official_pet_state_path()
        self._official_signature = None
        self._official_target = None  # type: Optional[PetTarget]
        self.last_visual_metrics = {}  # type: Dict[str, float]

    def _refresh_windows(self) -> None:
        now = time.monotonic()
        if now - self._last_window_scan >= 1.0:
            self._windows = enumerate_codex_windows()
            self._last_window_scan = now

    def _read_official_target_cached(self) -> Optional[PetTarget]:
        """Parse the large global state only when Codex actually rewrites it."""
        try:
            stat = self._official_path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            self._official_signature = None
            self._official_target = None
            return None
        if signature == self._official_signature:
            return self._official_target
        try:
            with self._official_path.open("r", encoding="utf-8-sig") as stream:
                payload = json.load(stream)
        except (OSError, TypeError, ValueError):
            # Electron may be between truncate/write operations. Keep the last
            # good position and retry because the signature is not committed.
            return self._official_target
        self._official_target = parse_official_pet_state(payload, _screen_scale())
        self._official_signature = signature
        return self._official_target

    def locate(self) -> Optional[PetTarget]:
        self._refresh_windows()
        # Codex itself persists the floating pet's logical desktop position.
        # This is deterministic and also updates while the pet is dragged.
        official = self._read_official_target_cached()
        codex_visible = any(item.visible and not item.cloaked for item in self._windows)
        if official is not None and codex_visible:
            x, y, _left_down = cursor_state()
            left, top, right, bottom = official.rect
            if left <= x < right and top <= y < bottom:
                self.last_visual_metrics = {"officialState": 1.0}
                return official
            self.last_visual_metrics = {"officialState": 1.0, "outsidePet": 1.0}
            return None

        # Compatibility fallback for client versions that do not persist pet
        # state. It samples only the small patch around the cursor.
        for item in self._windows:
            if item.score >= 10:
                return PetTarget(
                    hwnd=item.hwnd,
                    process_id=item.process_id,
                    rect=item.rect,
                    score=item.score,
                    class_name=item.class_name,
                    confidence="independent-window",
                )

        x, y, _left_down = cursor_state()
        main = None
        for item in self._windows:
            left, top, right, bottom = item.rect
            width = right - left
            height = bottom - top
            if item.visible and not item.cloaked and width >= 700 and height >= 400 and left <= x < right and top <= y < bottom:
                main = item
                break
        if main is None:
            self.last_visual_metrics = {}
            return None

        left, top, right, _bottom = main.rect
        if y > top + min(220, max(120, int((right - left) * 0.18))):
            self.last_visual_metrics = {"reason": -1.0}
            return None
        half = PET_SAMPLE_SIZE // 2
        pixels = _capture_patch(x - half, y - half, PET_SAMPLE_SIZE, PET_SAMPLE_SIZE)
        matched, metrics = classify_pet_pixels(pixels)
        self.last_visual_metrics = metrics
        if not matched:
            return None
        return PetTarget(
            hwnd=main.hwnd,
            process_id=main.process_id,
            rect=(x - half, y - half, x + half, y + half),
            score=int(metrics.get("score", 0)),
            class_name=main.class_name,
            confidence="cursor-visual-match",
        )


def diagnostics_as_dicts():
    return [asdict(item) for item in enumerate_codex_windows()]
