"""
Gamepad to Keyboard Mapper
----------------------------------
این برنامه ورودی‌های دسته‌ی بازی (دکمه‌ها، D-pad و آنالوگ استیک‌ها) را می‌خواند
و آن‌ها را به فشردن کلیدهای کیبرد یا کلیک/اسکرول ماوس تبدیل می‌کند تا بازی‌هایی که
فقط ورودی کیبرد/ماوس یا دسته‌ی PS4/XInput استاندارد را می‌شناسند، با دسته‌ی شما هم
قابل بازی باشند.

نیازمندی‌ها (یک‌بار نصب کنید):
    pip install pygame keyboard mouse

اجرا:
    python gamepad_to_keyboard.py

نکته‌ی مهم: چون کتابخانه‌ی keyboard برای شبیه‌سازی سراسری کلید نیاز به دسترسی سطح
پایین دارد، در ویندوز باید این برنامه را با دسترسی Administrator اجرا کنید تا در
همه‌ی بازی‌ها (به‌خصوص بازی‌های اجراشده با دسترسی بالاتر) کار کند.
"""

import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pygame
import keyboard as kb
import mouse as ms

# ---------------------------------------------------------------------------
# تزریق کلید مبتنی بر Scan Code (کد سخت‌افزاری) به‌جای Virtual-Key
# ---------------------------------------------------------------------------
# بعضی بازی‌ها (مثل سری Forza) از DirectInput/RawInput برای خواندن کیبرد استفاده
# می‌کنند و فقط به کدهای سخت‌افزاری واقعی کیبرد واکنش نشان می‌دهند، نه به کدهای
# Virtual-Key که کتابخانه‌ی keyboard به‌صورت پیش‌فرض می‌فرستد. این کلاس با فراخوانی
# مستقیم SendInput ویندوز و پرچم KEYEVENTF_SCANCODE، ورودی را تا حد امکان شبیه به
# فشردن واقعی کلید روی کیبرد فیزیکی می‌کند.

# جدول کد سخت‌افزاری کیبرد (Set 1) برای کلیدهای پرکاربرد
SCANCODES = {
    "esc": 0x01, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06,
    "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B,
    "-": 0x0C, "=": 0x0D, "backspace": 0x0E, "tab": 0x0F,
    "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14, "y": 0x15,
    "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19, "[": 0x1A, "]": 0x1B,
    "enter": 0x1C,
    "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21, "g": 0x22, "h": 0x23,
    "j": 0x24, "k": 0x25, "l": 0x26, ";": 0x27, "'": 0x28, "`": 0x29,
    "shift": 0x2A, "left shift": 0x2A, "\\": 0x2B,
    "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30, "n": 0x31,
    "m": 0x32, ",": 0x33, ".": 0x34, "/": 0x35, "right shift": 0x36,
    "*": 0x37, "alt": 0x38, "left alt": 0x38, "space": 0x39,
    "caps lock": 0x3A,
    "f1": 0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F,
    "f6": 0x40, "f7": 0x41, "f8": 0x42, "f9": 0x43, "f10": 0x44,
    "num lock": 0x45, "scroll lock": 0x46,
    "home": 0x47, "up": 0x48, "page up": 0x49,
    "left": 0x4B, "right": 0x4D,
    "end": 0x4F, "down": 0x50, "page down": 0x51,
    "insert": 0x52, "delete": 0x53,
    "f11": 0x57, "f12": 0x58,
    "ctrl": 0x1D, "left ctrl": 0x1D,
    "right ctrl": 0x1D,   # اکستندد
    "right alt": 0x38,    # اکستندد
}

# کلیدهایی که در سخت‌افزار واقعی با پیشوند 0xE0 (Extended) ارسال می‌شوند
EXTENDED_SCAN_KEYS = {
    "right ctrl", "right alt", "up", "down", "left", "right",
    "home", "end", "insert", "delete", "page up", "page down",
    "num lock",
}


class ScanCodeInjector:
    """تزریق کلید با SendInput ویندوز و پرچم KEYEVENTF_SCANCODE."""

    KEYEVENTF_SCANCODE = 0x0008
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_EXTENDEDKEY = 0x0001
    INPUT_KEYBOARD = 1

    def __init__(self):
        self._available = sys.platform.startswith("win")
        if self._available:
            self._setup_ctypes()

    def _setup_ctypes(self):
        import ctypes

        self._ctypes = ctypes
        PUL = ctypes.POINTER(ctypes.c_ulong)

        class KeyBdInput(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL),
            ]

        class HardwareInput(ctypes.Structure):
            _fields_ = [
                ("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort),
            ]

        class MouseInput(ctypes.Structure):
            _fields_ = [
                ("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL),
            ]

        class InputUnion(ctypes.Union):
            _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]

        class InputStruct(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong), ("ii", InputUnion)]

        self._KeyBdInput = KeyBdInput
        self._InputUnion = InputUnion
        self._InputStruct = InputStruct

    def supports(self, key_name):
        return key_name in SCANCODES

    def _send(self, key_name, key_up):
        scan_code = SCANCODES.get(key_name)
        if scan_code is None or not self._available:
            return False

        ctypes = self._ctypes
        flags = self.KEYEVENTF_SCANCODE
        if key_up:
            flags |= self.KEYEVENTF_KEYUP
        if key_name in EXTENDED_SCAN_KEYS:
            flags |= self.KEYEVENTF_EXTENDEDKEY

        extra = ctypes.c_ulong(0)
        ii_ = self._InputUnion()
        ii_.ki = self._KeyBdInput(0, scan_code, flags, 0, ctypes.pointer(extra))
        x = self._InputStruct(self.INPUT_KEYBOARD, ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
        return True

    def press(self, key_name):
        return self._send(key_name, key_up=False)

    def release(self, key_name):
        return self._send(key_name, key_up=True)


MOUSE_LABELS = {
    "mouse:left": "کلیک چپ ماوس",
    "mouse:right": "کلیک راست ماوس",
    "mouse:middle": "کلیک وسط ماوس",
    "mouse:scroll_up": "چرخ اسکرول (بالا)",
    "mouse:scroll_down": "چرخ اسکرول (پایین)",
}


def format_output_label(key):
    """برای نمایش خوانا در جدول؛ برای کلیدهای کیبرد همان متن اصلی برمی‌گردد."""
    return MOUSE_LABELS.get(key, key)


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gamepad_mapping.json")
AXIS_THRESHOLD_DEFAULT = 0.5
POLL_INTERVAL = 0.008  # حدود 125 بار در ثانیه


# ---------------------------------------------------------------------------
# مدیریت تنظیمات (ذخیره/بارگذاری فایل JSON)
# ---------------------------------------------------------------------------
class ConfigManager:
    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self.data = {
            "device_name": None,
            "buttons": {},   # {"0": "w", "1": "s", ...}
            "hats": {},      # {"0": {"up": "up", "down": "down", "left": "left", "right": "right"}}
            "axes": {},      # {"0": {"positive": "d", "negative": "a", "threshold": 0.5}}
            "injection_mode": "vk",   # "vk" (پیش‌فرض) یا "scancode" (سازگاری با بازی‌های سخت‌گیر مثل Forza)
        }

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                messagebox.showwarning("خطا در بارگذاری", f"فایل تنظیمات خوانده نشد:\n{e}")
        return self.data

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("خطا در ذخیره‌سازی", f"فایل تنظیمات ذخیره نشد:\n{e}")

    def save_as(self, path):
        self.path = path
        self.save()

    def load_from(self, path):
        self.path = path
        return self.load()


# ---------------------------------------------------------------------------
# لایه‌ی ارتباط با دسته (pygame joystick)
# ---------------------------------------------------------------------------
class GamepadReader:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        self.joystick = None

    def list_devices(self):
        pygame.joystick.quit()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        names = []
        for i in range(count):
            j = pygame.joystick.Joystick(i)
            j.init()
            names.append(f"{i}: {j.get_name()}")
        return names

    def open(self, index):
        if self.joystick is not None:
            try:
                self.joystick.quit()
            except Exception:
                pass
        self.joystick = pygame.joystick.Joystick(index)
        self.joystick.init()
        return self.joystick

    def pump(self):
        pygame.event.pump()

    def get_button_count(self):
        return self.joystick.get_numbuttons() if self.joystick else 0

    def get_hat_count(self):
        return self.joystick.get_numhats() if self.joystick else 0

    def get_axis_count(self):
        return self.joystick.get_numaxes() if self.joystick else 0

    def get_button(self, i):
        return self.joystick.get_button(i)

    def get_hat(self, i):
        return self.joystick.get_hat(i)  # (x, y) با مقادیر -1، 0، 1

    def get_axis(self, i):
        return self.joystick.get_axis(i)


# ---------------------------------------------------------------------------
# ترد شنود برای «یادگیری» ورودی دسته هنگام تنظیم نگاشت
# ---------------------------------------------------------------------------
class InputListener:
    """یک بار یک ورودی از دسته (دکمه، جهت D-pad یا جهت آنالوگ) را می‌گیرد."""

    def __init__(self, reader: GamepadReader):
        self.reader = reader

    def capture_next_input(self, timeout=15.0):
        """
        برمی‌گرداند: تاپلی از نوع ("button", index) یا ("hat", index, direction)
        یا ("axis", index, "positive"/"negative")
        اگر چیزی گرفته نشد None برمی‌گرداند.
        """
        start = time.time()
        n_buttons = self.reader.get_button_count()
        n_hats = self.reader.get_hat_count()
        n_axes = self.reader.get_axis_count()

        prev_buttons = [self.reader.get_button(i) for i in range(n_buttons)]
        prev_hats = [self.reader.get_hat(i) for i in range(n_hats)]
        prev_axes = [self.reader.get_axis(i) for i in range(n_axes)]

        while time.time() - start < timeout:
            self.reader.pump()

            for i in range(n_buttons):
                val = self.reader.get_button(i)
                if val and not prev_buttons[i]:
                    return ("button", i)
                prev_buttons[i] = val

            for i in range(n_hats):
                x, y = self.reader.get_hat(i)
                px, py = prev_hats[i]
                if (x, y) != (0, 0) and (px, py) == (0, 0):
                    direction = None
                    if x == 1:
                        direction = "right"
                    elif x == -1:
                        direction = "left"
                    elif y == 1:
                        direction = "up"
                    elif y == -1:
                        direction = "down"
                    if direction:
                        return ("hat", i, direction)
                prev_hats[i] = (x, y)

            for i in range(n_axes):
                val = self.reader.get_axis(i)
                if abs(val) > AXIS_THRESHOLD_DEFAULT and abs(prev_axes[i]) <= AXIS_THRESHOLD_DEFAULT:
                    direction = "positive" if val > 0 else "negative"
                    return ("axis", i, direction)
                prev_axes[i] = val

            time.sleep(0.01)
        return None


# ---------------------------------------------------------------------------
# موتور شبیه‌سازی: نگاشت را می‌خواند و کلید کیبرد را فشار/رها می‌کند
# ---------------------------------------------------------------------------
class EmulationEngine:
    def __init__(self, reader: GamepadReader, config: ConfigManager):
        self.reader = reader
        self.config = config
        self._running = False
        self._thread = None
        self._pressed_keys = set()
        self._last_scroll = {}          # throttle برای اسکرول پیوسته
        self._scroll_interval = 0.08    # فاصله‌ی هر تیک اسکرول هنگام نگه‌داشتن دکمه (ثانیه)
        self._scan_injector = ScanCodeInjector()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        # هر کلید/دکمه‌ای که فشرده مانده را رها کن
        for key in list(self._pressed_keys):
            self._release_raw(key)
        self._pressed_keys.clear()

    @staticmethod
    def _is_scroll(key):
        return key in ("mouse:scroll_up", "mouse:scroll_down")

    @staticmethod
    def _is_mouse(key):
        return key.startswith("mouse:")

    def _use_scancode(self):
        return self.config.data.get("injection_mode") == "scancode"

    def _kb_press(self, key):
        # اگر حالت سازگاری (Scan Code) فعال است و این کلید در جدول Scan Code موجود
        # است، از تزریق سخت‌افزاری استفاده کن؛ در غیر این صورت fallback به کتابخانه‌ی keyboard
        if self._use_scancode() and self._scan_injector.supports(key):
            if self._scan_injector.press(key):
                return
        kb.press(key)

    def _kb_release(self, key):
        if self._use_scancode() and self._scan_injector.supports(key):
            if self._scan_injector.release(key):
                return
        kb.release(key)

    def _release_raw(self, key):
        try:
            if self._is_scroll(key):
                return  # اسکرول حالت «نگه‌داشته» ندارد
            if self._is_mouse(key):
                ms.release(key.split(":", 1)[1])
            else:
                self._kb_release(key)
        except Exception:
            pass

    def _press(self, key):
        if not key:
            return

        # چرخ اسکرول: هر بار که دکمه نگه داشته شده، با فاصله‌ی زمانی مشخص یک تیک اسکرول بزن
        if self._is_scroll(key):
            now = time.time()
            last = self._last_scroll.get(key, 0)
            if now - last >= self._scroll_interval:
                try:
                    ms.wheel(1 if key.endswith("scroll_up") else -1)
                except Exception:
                    pass
                self._last_scroll[key] = now
            return

        if key in self._pressed_keys:
            return
        try:
            if self._is_mouse(key):
                ms.press(key.split(":", 1)[1])
            else:
                self._kb_press(key)
            self._pressed_keys.add(key)
        except Exception:
            pass

    def _release(self, key):
        if not key or self._is_scroll(key):
            return
        if key in self._pressed_keys:
            self._release_raw(key)
            self._pressed_keys.discard(key)

    def _loop(self):
        buttons_map = self.config.data.get("buttons", {})
        hats_map = self.config.data.get("hats", {})
        axes_map = self.config.data.get("axes", {})

        # وضعیت قبلی برای تشخیص فشرده‌شدن/رهاشدن جهت‌ها
        hat_state = {}
        axis_state = {}

        while self._running:
            try:
                self.reader.pump()

                # دکمه‌های معمولی
                for idx_str, key in buttons_map.items():
                    idx = int(idx_str)
                    if idx >= self.reader.get_button_count():
                        continue
                    pressed = self.reader.get_button(idx)
                    if pressed:
                        self._press(key)
                    else:
                        self._release(key)

                # D-pad (hat)
                for idx_str, directions in hats_map.items():
                    idx = int(idx_str)
                    if idx >= self.reader.get_hat_count():
                        continue
                    x, y = self.reader.get_hat(idx)
                    current = set()
                    if x == 1:
                        current.add("right")
                    elif x == -1:
                        current.add("left")
                    if y == 1:
                        current.add("up")
                    elif y == -1:
                        current.add("down")

                    prev = hat_state.get(idx, set())
                    for d, key in directions.items():
                        if d in current and d not in prev:
                            self._press(key)
                        elif d not in current and d in prev:
                            self._release(key)
                    hat_state[idx] = current

                # آنالوگ استیک‌ها (axes)
                for idx_str, cfg in axes_map.items():
                    idx = int(idx_str)
                    if idx >= self.reader.get_axis_count():
                        continue
                    val = self.reader.get_axis(idx)
                    threshold = cfg.get("threshold", AXIS_THRESHOLD_DEFAULT)
                    pos_key = cfg.get("positive")
                    neg_key = cfg.get("negative")

                    prev = axis_state.get(idx, "neutral")
                    if val > threshold:
                        state = "positive"
                    elif val < -threshold:
                        state = "negative"
                    else:
                        state = "neutral"

                    if state != prev:
                        if prev == "positive":
                            self._release(pos_key)
                        elif prev == "negative":
                            self._release(neg_key)
                        if state == "positive":
                            self._press(pos_key)
                        elif state == "negative":
                            self._press(neg_key)
                        axis_state[idx] = state

                time.sleep(POLL_INTERVAL)
            except Exception:
                # اگر دسته موقتاً قطع شد، حلقه را متوقف نکن
                time.sleep(0.1)


# ---------------------------------------------------------------------------
# رابط گرافیکی
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("نگاشت دسته به کیبرد")
        self.root.geometry("640x560")

        self.config = ConfigManager()
        self.config.load()
        self.reader = GamepadReader()
        self.listener = InputListener(self.reader)
        self.engine = EmulationEngine(self.reader, self.config)

        self._build_ui()
        self._refresh_devices()
        self._refresh_mapping_list()

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="دسته‌ی متصل:").pack(side="right", padx=5)
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(top, textvariable=self.device_var, state="readonly", width=40)
        self.device_combo.pack(side="right", padx=5)

        ttk.Button(top, text="بروزرسانی لیست", command=self._refresh_devices).pack(side="right", padx=5)
        ttk.Button(top, text="اتصال", command=self._connect_device).pack(side="right", padx=5)

        mid = ttk.Frame(self.root, padding=10)
        mid.pack(fill="both", expand=True)

        columns = ("type", "source", "key", "raw")
        self.tree = ttk.Treeview(mid, columns=columns, show="headings", height=15,
                                  displaycolumns=("type", "source", "key"))
        self.tree.heading("type", text="نوع ورودی")
        self.tree.heading("source", text="مبدأ (دسته)")
        self.tree.heading("key", text="کلید معادل (کیبرد/ماوس)")
        self.tree.column("type", width=100, anchor="center")
        self.tree.column("source", width=200, anchor="center")
        self.tree.column("key", width=180, anchor="center")
        self.tree.pack(fill="both", expand=True, side="right")

        scroll = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(fill="y", side="left")

        btns = ttk.Frame(self.root, padding=10)
        btns.pack(fill="x")

        ttk.Button(btns, text="+ افزودن نگاشت جدید", command=self._add_mapping).pack(side="right", padx=5)
        ttk.Button(btns, text="حذف نگاشت انتخاب‌شده", command=self._delete_mapping).pack(side="right", padx=5)
        ttk.Button(btns, text="ذخیره در فایل...", command=self._save_as).pack(side="left", padx=5)
        ttk.Button(btns, text="بارگذاری از فایل...", command=self._load_from).pack(side="left", padx=5)

        control = ttk.Frame(self.root, padding=10)
        control.pack(fill="x")

        self.status_var = tk.StringVar(value="آماده")
        ttk.Label(control, textvariable=self.status_var, foreground="blue").pack(side="right", padx=5)

        self.toggle_btn = ttk.Button(control, text="شروع فعالیت دسته", command=self._toggle_emulation)
        self.toggle_btn.pack(side="left", padx=5)

        self.scancode_var = tk.BooleanVar(
            value=(self.config.data.get("injection_mode") == "scancode")
        )
        scancode_check = ttk.Checkbutton(
            control,
            text="حالت سازگاری با بازی‌های سخت‌گیر (Forza و مشابه) — ارسال کد سخت‌افزاری کلید",
            variable=self.scancode_var,
            command=self._on_toggle_scancode_mode,
        )
        scancode_check.pack(side="left", padx=15)

    # ---------------- منطق ----------------
    def _refresh_devices(self):
        devices = self.reader.list_devices()
        self.device_combo["values"] = devices
        if devices:
            saved_name = self.config.data.get("device_name")
            match = next((d for d in devices if saved_name and saved_name in d), devices[0])
            self.device_var.set(match)
        else:
            self.device_var.set("")
            self.status_var.set("هیچ دسته‌ای شناسایی نشد")

    def _connect_device(self):
        val = self.device_var.get()
        if not val:
            messagebox.showwarning("توجه", "ابتدا یک دسته را از لیست انتخاب کنید.")
            return
        index = int(val.split(":")[0])
        joystick = self.reader.open(index)
        self.config.data["device_name"] = joystick.get_name()
        self.status_var.set(f"متصل به: {joystick.get_name()}")

    def _refresh_mapping_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for idx, key in self.config.data.get("buttons", {}).items():
            self.tree.insert("", "end", values=("دکمه", f"دکمه #{idx}", format_output_label(key), key))

        for idx, directions in self.config.data.get("hats", {}).items():
            for d, key in directions.items():
                label = {"up": "بالا", "down": "پایین", "left": "چپ", "right": "راست"}.get(d, d)
                self.tree.insert("", "end", values=("D-pad", f"D-pad #{idx} / {label}", format_output_label(key), key))

        for idx, cfg in self.config.data.get("axes", {}).items():
            if cfg.get("positive"):
                self.tree.insert("", "end", values=("آنالوگ", f"محور #{idx} / مثبت", format_output_label(cfg["positive"]), cfg["positive"]))
            if cfg.get("negative"):
                self.tree.insert("", "end", values=("آنالوگ", f"محور #{idx} / منفی", format_output_label(cfg["negative"]), cfg["negative"]))

    def _add_mapping(self):
        if self.reader.joystick is None:
            messagebox.showwarning("توجه", "ابتدا یک دسته را متصل کنید.")
            return

        self.status_var.set("یک دکمه یا جهت روی دسته فشار دهید... (۱۵ ثانیه فرصت دارید)")
        self.root.update()

        def worker():
            result = self.listener.capture_next_input(timeout=15.0)
            self.root.after(0, lambda: self._after_capture_gamepad(result))

        threading.Thread(target=worker, daemon=True).start()

    def _after_capture_gamepad(self, result):
        if result is None:
            self.status_var.set("چیزی دریافت نشد. دوباره تلاش کنید.")
            return

        self.status_var.set("حالا کلید کیبرد یا دکمه/اسکرول ماوس معادل را فشار دهید...")
        self.root.update()

        def worker():
            captured = {}
            stop_event = threading.Event()

            def on_key(event):
                if "value" in captured:
                    return
                # از گرفتن رویداد رهاشدن کلید جلوگیری می‌کنیم، فقط لحظه‌ی فشرده‌شدن مهم است
                if getattr(event, "event_type", "down") != "down":
                    return
                captured["value"] = event.name
                stop_event.set()

            def on_mouse(event):
                if "value" in captured:
                    return
                # کلیک دکمه‌های ماوس
                if isinstance(event, ms.ButtonEvent) and event.event_type == "down":
                    if event.button in ("left", "right", "middle"):
                        captured["value"] = f"mouse:{event.button}"
                        stop_event.set()
                # چرخش قرقره‌ی ماوس
                elif isinstance(event, ms.WheelEvent):
                    direction = "scroll_up" if event.delta > 0 else "scroll_down"
                    captured["value"] = f"mouse:{direction}"
                    stop_event.set()
                # رویدادهای حرکت ماوس (MoveEvent) نادیده گرفته می‌شوند

            kb_hook = kb.hook(on_key)
            ms_hook = ms.hook(on_mouse)
            stop_event.wait(timeout=15.0)
            try:
                kb.unhook(kb_hook)
            except Exception:
                pass
            try:
                ms.unhook(ms_hook)
            except Exception:
                pass
            self.root.after(0, lambda: self._after_capture_output(result, captured.get("value")))

        threading.Thread(target=worker, daemon=True).start()

    def _after_capture_output(self, gamepad_result, output_key):
        if not output_key:
            self.status_var.set("چیزی دریافت نشد. دوباره تلاش کنید.")
            return

        kind = gamepad_result[0]
        if kind == "button":
            _, idx = gamepad_result
            self.config.data["buttons"][str(idx)] = output_key
        elif kind == "hat":
            _, idx, direction = gamepad_result
            self.config.data["hats"].setdefault(str(idx), {})[direction] = output_key
        elif kind == "axis":
            _, idx, direction = gamepad_result
            entry = self.config.data["axes"].setdefault(str(idx), {"threshold": AXIS_THRESHOLD_DEFAULT})
            entry[direction] = output_key

        self.config.save()
        self._refresh_mapping_list()
        self.status_var.set(f"نگاشت ذخیره شد: {kind} → {format_output_label(output_key)}")

    def _delete_mapping(self):
        selected = self.tree.selection()
        if not selected:
            return
        for item_id in selected:
            values = self.tree.item(item_id, "values")
            type_label, source_label, _display_key, key = values
            if type_label == "دکمه":
                idx = source_label.split("#")[1]
                self.config.data["buttons"].pop(idx, None)
            elif type_label == "D-pad":
                idx = source_label.split("#")[1].split(" ")[0]
                if idx in self.config.data["hats"]:
                    to_remove = [d for d, k in self.config.data["hats"][idx].items() if k == key]
                    for d in to_remove:
                        self.config.data["hats"][idx].pop(d, None)
                    if not self.config.data["hats"][idx]:
                        self.config.data["hats"].pop(idx, None)
            elif type_label == "آنالوگ":
                idx = source_label.split("#")[1].split(" ")[0]
                if idx in self.config.data["axes"]:
                    for direction in ("positive", "negative"):
                        if self.config.data["axes"][idx].get(direction) == key:
                            self.config.data["axes"][idx].pop(direction, None)
                    if not any(d in self.config.data["axes"][idx] for d in ("positive", "negative")):
                        self.config.data["axes"].pop(idx, None)

        self.config.save()
        self._refresh_mapping_list()

    def _save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            self.config.save_as(path)
            self.status_var.set(f"ذخیره شد در: {path}")

    def _load_from(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            self.config.load_from(path)
            self._refresh_mapping_list()
            self.status_var.set(f"بارگذاری شد از: {path}")

    def _toggle_emulation(self):
        if self.engine._running:
            self.engine.stop()
            self.toggle_btn.config(text="شروع فعالیت دسته")
            self.status_var.set("فعالیت دسته متوقف شد.")
        else:
            if self.reader.joystick is None:
                messagebox.showwarning("توجه", "ابتدا یک دسته را متصل کنید.")
                return
            self.engine.start()
            self.toggle_btn.config(text="توقف فعالیت دسته")
            self.status_var.set("فعالیت دسته آغاز شد. کلیدهای کیبرد اکنون از دسته فرمان می‌گیرند.")

    def _on_toggle_scancode_mode(self):
        self.config.data["injection_mode"] = "scancode" if self.scancode_var.get() else "vk"
        self.config.save()
        if self.scancode_var.get():
            self.status_var.set(
                "حالت سازگاری فعال شد. کلیدهایی که در جدول Scan Code پشتیبانی نمی‌شوند "
                "همچنان با روش قبلی ارسال می‌شوند."
            )
        else:
            self.status_var.set("حالت سازگاری غیرفعال شد؛ روش استاندارد استفاده می‌شود.")

    def on_close(self):
        self.engine.stop()
        self.config.save()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
