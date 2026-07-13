# joyestick
using joyestick for windows games. All game you imagine!!

# 🎮 Gamepad to Keyboard Mapper

Turn any gamepad into a keyboard/mouse — and play games that don't officially support your controller.

Many games only accept keyboard input or a standard XInput/PS4 controller. This tool reads your gamepad's buttons, D-pad, and analog sticks, then instantly translates them into keyboard presses or mouse clicks/scrolls. As far as the game is concerned, you're just typing on a keyboard.

## ✨ Features

- 🕹️ Works with any gamepad supported by Windows (PS1/PS2/PS3 via adapter, Xbox 360, PC, Android controllers, etc.)
- ⌨️ Map buttons, D-pad directions, and analog stick directions to **any keyboard key**
- 🖱️ Also supports **left click, right click, middle click, and scroll wheel**
- 💾 Save/load multiple mapping profiles — one per game
- 🛠️ **Compatibility mode** for strict games (like Forza) that ignore normal simulated key presses
- 🟢 Simple point-and-click setup — no manual config editing required

## 📦 Installation

**Requirements:** Python 3 for Windows — [download here](https://www.python.org/downloads/)

```bash
pip install -r requirements.txt
```

## ▶️ Running

> ⚠️ **Run as Administrator.** The `keyboard` and `mouse` libraries need low-level access to simulate global input — without admin rights, some games (especially those running elevated) won't respond.

```bash
python gamepad_to_keyboard.py
```

## 🚀 How to Use

1. **Connect** — Plug in your gamepad, click **"Refresh List"**, select it, then click **"Connect"**.
2. **Map a button** — Click **"+ Add New Mapping"**, then:
   - Press a button / D-pad direction / stick direction on your gamepad
   - Immediately press the matching key on your keyboard — or click/scroll your mouse
   - It's saved automatically ✅
3. **Repeat** for every button and direction you want mapped.
4. **Remove a mapping** — Select it in the list and click **"Remove Selected Mapping"**.
5. **Save profiles** — Mappings are auto-saved to `gamepad_mapping.json`. Use **"Save As..."** / **"Load From..."** to keep separate profiles per game.
6. **Go live** — Click **"Start Gamepad Activity"**. From now on, your gamepad drives the keyboard/mouse — while your real keyboard still works too.
7. Click the same button again (now labeled **"Stop Gamepad Activity"**) to stop.

## 🏎️ Troubleshooting: Game Not Responding? (e.g. Forza 6)

Some strict games (racing sims especially) need extra help. There are two possible causes:

### Case 1 — The game doesn't detect the key press at all

Some games read keyboard input via DirectInput/RawInput and only respond to a key's **real hardware scan code**, not a standard simulated key press.

**Fix:** Check the box labeled **"Compatibility mode for strict games (Forza & similar)"** at the bottom of the app. This switches keyboard injection to use Windows' low-level `SendInput` with hardware scan codes — much closer to a real physical key press.

### Case 2 — The game detects a gamepad is connected and ignores the keyboard entirely

Many racing games auto-switch to "controller mode" the moment *any* gamepad/HID device is plugged in — even if they don't recognize its buttons. This isn't a bug in this tool; it's the game's own detection logic.

**Fix:** Hide the physical gamepad from the game (but not from this app) using the free tool **[HidHide](https://github.com/nefarius/HidHide)**:
1. Install HidHide.
2. Add your gamepad to the **"Hidden devices"** list.
3. Add `python.exe` (or your compiled `.exe`) to the **"Allowed applications"** list.
4. Now the game can't see the gamepad at all — but this tool still can, and keeps sending keyboard input normally.

💡 Try both fixes together if one alone doesn't work.

## 📦 Turning it into a Standalone .exe

Want to run this without opening Python or a terminal every time? Turn it into a normal double-clickable `.exe` — no console/cmd window, just like any other Windows app.

**Easiest way:** put `build_exe.bat` in the same folder as `gamepad_to_keyboard.py`, then double-click it. It will:
1. Install everything needed (including [PyInstaller](https://pyinstaller.org/))
2. Build a single `.exe` file with **no console window**
3. Automatically request **Administrator rights** when launched (so you don't have to right-click → "Run as Administrator" every time)

Your finished app will appear at `dist\GamepadMapper.exe` — you can move that one file anywhere, rename it, pin it to your taskbar, whatever you like.

**Manual way**, if you'd rather run the command yourself:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --uac-admin --name "GamepadMapper" gamepad_to_keyboard.py
```

| Flag | What it does |
|---|---|
| `--onefile` | Packs everything into a single `.exe` (easier to share) |
| `--windowed` | **No console window** — opens like a normal app |
| `--uac-admin` | Auto-prompts for Administrator rights on launch |

⚠️ Antivirus/Windows Defender sometimes flags freshly-built PyInstaller `.exe` files as suspicious (a known false-positive with PyInstaller, not an actual virus). If that happens, just add an exception for `GamepadMapper.exe`.

## 📝 Notes

- Default analog stick threshold is `0.5` (stick must be pushed past the halfway point to trigger). Edit `"threshold"` in `gamepad_mapping.json` to fine-tune.
- Mouse clicks are fully "hold-able" — perfect for dragging or holding fire.
- Scroll wheel simulates continuous scrolling (one tick every `0.08s`) while the mapped button is held — adjust `self._scroll_interval` in the code if needed.
- Scan-code compatibility mode currently supports common keys (letters, numbers, arrows, F-keys, Space, Enter, Shift, Ctrl, Alt, etc.). Unsupported keys automatically fall back to the standard method.
- If your gamepad isn't detected, make sure Windows sees it under **Devices and Printers → Game Controllers**.
