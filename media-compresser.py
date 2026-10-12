#!/usr/bin/env python3
"""
ULTRA COMPRESSOR - Termux (Curses TUI)
Author : Musaddiq Shah.am
Version: 3.0.0

Controls:
- Up / Down arrows : navigate menu
- Left / Right     : switch pages (main <-> info)
- Enter / Space    : select
- Esc              : back / quit
- q                : quit
- Ctrl+C           : force exit
"""

import os
import sys
import re
import time
import shutil
import threading
import subprocess
import traceback
import curses
from pathlib import Path


# ==================================================
#   AUTHOR
# ==================================================
AUTHOR  = "Musaddiq Shah.am"
VERSION = "3.0.0"


# ==================================================
#   FILE TYPES
# ==================================================
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".m4v"}
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".heic"}


# ==================================================
#   DEVICE INFO
# ==================================================
def get_cpu_cores():
    return os.cpu_count() or 1


def get_total_ram_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 0


def get_free_ram_mb():
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    mem[key] = int(val)
            if "MemAvailable" in mem:
                return mem["MemAvailable"] // 1024
            return mem.get("MemFree", 0) // 1024
    except Exception:
        return 0


def suggest_preset():
    cores = get_cpu_cores()
    ram = get_total_ram_mb()
    if cores >= 6 and ram >= 3500:
        return "1", "Good device"
    if cores >= 4 and ram >= 2500:
        return "1", "Mid device"
    if cores >= 4 and ram >= 1500:
        return "2", "Mid-low device"
    return "3", "Low device"


# ==================================================
#   PRESETS
# ==================================================
PRESETS = {
    "1": {
        "label": "Best Size",
        "desc": "libx265 CRF28->CRF36 (smallest file)",
        "attempts": [
            ("medium", "libx265", 28, "64k", None),
            ("medium", "libx265", 32, "48k", None),
            ("faster", "libx265", 36, "32k", "1280:720"),
        ],
        "min_ram_mb": 2000,
    },
    "2": {
        "label": "Small",
        "desc": "libx265 CRF30->CRF38 + 720p",
        "attempts": [
            ("fast", "libx265", 30, "48k", None),
            ("fast", "libx265", 34, "32k", "1280:720"),
            ("veryfast", "libx265", 38, "24k", "854:480"),
        ],
        "min_ram_mb": 1500,
    },
    "3": {
        "label": "Balanced",
        "desc": "libx264 CRF26->CRF34 (safe)",
        "attempts": [
            ("fast", "libx264", 26, "96k", None),
            ("faster", "libx264", 30, "64k", None),
            ("veryfast", "libx264", 34, "48k", "1280:720"),
        ],
        "min_ram_mb": 1000,
    },
    "4": {
        "label": "Fast",
        "desc": "libx264 CRF28->CRF36 (quick)",
        "attempts": [
            ("veryfast", "libx264", 28, "64k", None),
            ("veryfast", "libx264", 32, "48k", None),
            ("superfast", "libx264", 36, "32k", "1280:720"),
        ],
        "min_ram_mb": 800,
    },
    "5": {
        "label": "Ultra Fast",
        "desc": "libx264 ultrafast (quickest)",
        "attempts": [
            ("ultrafast", "libx264", 30, "48k", None),
            ("ultrafast", "libx264", 34, "32k", "1280:720"),
            ("ultrafast", "libx264", 38, "24k", "854:480"),
        ],
        "min_ram_mb": 500,
    },
}

PRESET_ORDER = ["1", "2", "3", "4", "5"]

IMAGE_QUALITY_MAP = {
    "1": [3, 5, 8, 12, 18, 25],
    "2": [4, 7, 10, 15, 20, 28],
    "3": [5, 8, 12, 18, 25, 31],
    "4": [6, 10, 15, 20, 26, 31],
    "5": [8, 12, 18, 25, 31, 31],
}


# ==================================================
#   HELPERS
# ==================================================
def human_size(b):
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.2f} {u}"
        b /= 1024
    return f"{b:.2f} TB"


def human_time(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def safe_name(name):
    name = name.strip().strip('"').strip("'")
    if not name:
        return None
    return re.sub(r'[<>:"/\\|?*]', "_", name) or None


def short_name(name, max_len):
    if len(name) <= max_len:
        return name.ljust(max_len)
    if max_len <= 1:
        return "."
    return name[:max_len - 1] + "~"


# ==================================================
#   DURATION
# ==================================================
def get_duration(path):
    if not shutil.which("ffprobe"):
        return 0
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception:
        return 0


# ==================================================
#   SCAN
# ==================================================
def scan_folder(folder):
    videos, audios, images = [], [], []
    try:
        entries = list(folder.iterdir())
    except Exception:
        return [], [], []

    for f in entries:
        try:
            if f.is_file():
                ext = f.suffix.lower()
                if ext in VIDEO_EXTS:
                    videos.append(f)
                elif ext in AUDIO_EXTS:
                    audios.append(f)
                elif ext in IMAGE_EXTS:
                    images.append(f)
        except Exception:
            continue

    videos.sort(key=lambda x: x.stat().st_size, reverse=True)
    audios.sort(key=lambda x: x.stat().st_size, reverse=True)
    images.sort(key=lambda x: x.stat().st_size, reverse=True)
    return videos, audios, images


# ==================================================
#   BUILD COMMANDS
# ==================================================
def build_video_cmd(src, dst, attempt):
    speed, codec, crf, abit, scale = attempt
    cmd = ["ffmpeg", "-y", "-i", str(src),
           "-vcodec", codec, "-crf", str(crf), "-preset", speed]
    if scale:
        cmd += ["-vf", f"scale={scale}"]
    cmd += ["-c:a", "aac", "-b:a", abit, str(dst)]
    return cmd


def build_audio_cmd(src, dst, abit):
    return ["ffmpeg", "-y", "-i", str(src), "-b:a", abit, str(dst)]


def build_image_cmd(src, dst, q, convert_to_jpg=False):
    cmd = ["ffmpeg", "-y", "-i", str(src), "-q:v", str(q)]
    if convert_to_jpg:
        cmd += ["-vf", "scale='min(1920,iw)':'-1'"]
    cmd.append(str(dst))
    return cmd


# ==================================================
#   FFMPEG (with terminal-safe progress)
# ==================================================
def run_ffmpeg_quiet(cmd, duration, progress_cb=None):
    """Run ffmpeg with optional progress callback (0-100)."""
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
            universal_newlines=True, bufsize=1
        )
        start = time.time()
        for line in proc.stderr:
            if "time=" in line and duration > 0 and progress_cb:
                try:
                    t = line.split("time=")[1].split(" ")[0]
                    h, m, s = t.split(":")
                    sec = int(h) * 3600 + int(m) * 60 + float(s)
                    pct = min(100, sec / duration * 100)
                    progress_cb(pct)
                except Exception:
                    pass
        proc.wait()
        if progress_cb:
            progress_cb(100)
        return proc.returncode == 0
    except Exception:
        return False


# ==================================================
#   SMART COMPRESS (no terminal output — curses handles UI)
# ==================================================
def smart_compress_video(src, dst, preset_key, progress_cb=None):
    old_size = src.stat().st_size
    duration = get_duration(src)
    attempts = PRESETS[preset_key]["attempts"]

    for attempt in attempts:
        cmd = build_video_cmd(src, dst, attempt)
        ok = run_ffmpeg_quiet(cmd, duration, progress_cb)
        if ok and dst.exists() and dst.stat().st_size < old_size:
            return True
        try:
            if dst.exists():
                dst.unlink()
        except Exception:
            pass
    return False


def smart_compress_audio(src, dst, preset_key, progress_cb=None):
    old_size = src.stat().st_size
    duration = get_duration(src)
    for br in ["64k", "48k", "32k", "24k", "16k"]:
        cmd = build_audio_cmd(src, dst, br)
        ok = run_ffmpeg_quiet(cmd, duration, progress_cb)
        if ok and dst.exists() and dst.stat().st_size < old_size:
            return True
        try:
            if dst.exists():
                dst.unlink()
        except Exception:
            pass
    return False


def smart_compress_image(src, dst, preset_key, progress_cb=None):
    old_size = src.stat().st_size
    ext = src.suffix.lower()
    convert_to_jpg = ext in {".png", ".bmp", ".tiff", ".tif", ".heic"}
    if convert_to_jpg and dst.suffix.lower() != ".jpg":
        dst = dst.with_suffix(".jpg")

    qualities = IMAGE_QUALITY_MAP.get(preset_key, [5, 10, 15, 20, 25, 31])
    for q in qualities:
        cmd = build_image_cmd(src, dst, q, convert_to_jpg=convert_to_jpg)
        ok = run_ffmpeg_quiet(cmd, 0, progress_cb)
        if ok and dst.exists() and dst.stat().st_size < old_size:
            return True, dst
        try:
            if dst.exists():
                dst.unlink()
        except Exception:
            pass
    return False, dst


def extract_audio_from_video(src, dst, progress_cb=None):
    duration = get_duration(src)
    cmd = ["ffmpeg", "-y", "-i", str(src), "-vn",
           "-c:a", "libmp3lame", "-b:a", "128k", str(dst)]
    return run_ffmpeg_quiet(cmd, duration, progress_cb)


# ==================================================
#   CURSES UI HELPERS
# ==================================================
def init_colors():
    """Setup color pairs. Call after curses.initscr()."""
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # title
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # success
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # warn
        curses.init_pair(4, curses.COLOR_RED, -1)      # error
        curses.init_pair(5, curses.COLOR_WHITE, -1)    # normal
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # highlight
        curses.init_pair(7, curses.COLOR_BLUE, -1)     # info
    except Exception:
        pass


def cp(n):
    """Get color pair safely."""
    try:
        return curses.color_pair(n)
    except Exception:
        return 0


def draw_center(stdscr, row, text, color=0, bold=False, width=None):
    """Draw centered text on a row."""
    h, w = stdscr.getmaxyx()
    if width is None:
        width = w
    x = max(0, (width - len(text)) // 2)
    attr = color
    if bold:
        attr |= curses.A_BOLD
    try:
        stdscr.addstr(row, x, text[:width - 1], attr)
    except curses.error:
        pass


def draw_box(stdscr, top, left, height, width, color=0):
    """Draw a simple ASCII box."""
    try:
        stdscr.addstr(top, left, "+" + "-" * (width - 2) + "+", color)
        for i in range(1, height - 1):
            stdscr.addstr(top + i, left, "|" + " " * (width - 2) + "|", color)
        stdscr.addstr(top + height - 1, left, "+" + "-" * (width - 2) + "+", color)
    except curses.error:
        pass


# ==================================================
#   CURSES MENU
# ==================================================
def curses_menu(stdscr, title, options, subtitle=""):
    """
    Arrow-key menu using curses.
    Returns: index (0-based) or None if cancelled.
    """
    curses.curs_set(0)
    selected = 0
    n = len(options)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Minimum size check
        if h < 10 or w < 40:
            try:
                stdscr.addstr(0, 0, "Terminal too small!", cp(4) | curses.A_BOLD)
                stdscr.addstr(1, 0, "Zoom out or enlarge terminal.")
                stdscr.addstr(2, 0, "Press q to quit.")
                stdscr.refresh()
            except curses.error:
                pass
            k = stdscr.getch()
            if k in (ord("q"), 27):
                return None
            continue

        # Header box (centered)
        box_w = min(w - 4, 60)
        box_left = (w - box_w) // 2
        box_top = max(1, h // 2 - (n // 2) - 5)

        draw_box(stdscr, box_top, box_left, 3, box_w, cp(1))
        draw_center(stdscr, box_top + 1, title, cp(1) | curses.A_BOLD, width=w)

        # Subtitle
        if subtitle:
            draw_center(stdscr, box_top + 4, subtitle, cp(7), width=w)

        # Options
        opt_start = box_top + 6
        for i, opt in enumerate(options):
            row = opt_start + i
            if row >= h - 3:
                break
            if i == selected:
                marker = "  > "
                attr = cp(6) | curses.A_BOLD | curses.A_REVERSE
            else:
                marker = "    "
                attr = cp(5)

            text = marker + opt
            x = box_left + 2
            try:
                stdscr.addstr(row, x, text[:box_w - 4], attr)
            except curses.error:
                pass

        # Footer
        footer = "Up/Down: Navigate  |  Enter: Select  |  Esc/q: Quit"
        draw_center(stdscr, h - 2, footer, cp(7) | curses.A_DIM, width=w)

        stdscr.refresh()

        # Input
        k = stdscr.getch()
        if k == curses.KEY_UP:
            selected = (selected - 1) % n
        elif k == curses.KEY_DOWN:
            selected = (selected + 1) % n
        elif k == curses.KEY_HOME:
            selected = 0
        elif k == curses.KEY_END:
            selected = n - 1
        elif k in (curses.KEY_ENTER, 10, 13, ord(" ")):
            return selected
        elif k in (27, ord("q"), ord("Q")):
            return None
        elif ord("1") <= k <= ord("9"):
            idx = k - ord("1")
            if 0 <= idx < n:
                return idx


# ==================================================
#   CURSES INPUT (single line)
# ==================================================
def curses_input(stdscr, title, prompt, default="", allow_empty=True):
    """Simple line input via curses."""
    curses.curs_set(1)
    curses.echo()

    h, w = stdscr.getmaxyx()
    stdscr.clear()

    box_w = min(w - 4, 60)
    box_left = (w - box_w) // 2
    box_top = max(1, h // 2 - 4)

    draw_box(stdscr, box_top, box_left, 3, box_w, cp(1))
    draw_center(stdscr, box_top + 1, title, cp(1) | curses.A_BOLD, width=w)

    if default:
        draw_center(stdscr, box_top + 4, f"(default: {default})", cp(7), width=w)

    # Input box
    input_row = box_top + 6
    try:
        stdscr.addstr(input_row, box_left, prompt + " ", cp(5) | curses.A_BOLD)
    except curses.error:
        pass

    stdscr.refresh()

    try:
        curses.curs_set(1)
        curses.echo()
        # Position cursor after prompt
        stdscr.move(input_row, box_left + len(prompt) + 1)
        stdscr.refresh()
        raw = stdscr.getstr(input_row, box_left + len(prompt) + 1, box_w - len(prompt) - 3)
        result = raw.decode("utf-8", errors="replace").strip()
    except curses.error:
        result = ""
    except Exception:
        result = ""
    finally:
        curses.noecho()
        curses.curs_set(0)

    if not result and default:
        return default
    if not result and not allow_empty:
        return None
    return result


# ==================================================
#   PROGRESS SCREEN (curses)
# ==================================================
def curses_progress(stdscr, title, items, worker_fn):
    """
    Show a progress screen while worker_fn runs.
    worker_fn(update_cb) where update_cb(idx, percent, status)
    Runs in background thread.
    """
    curses.curs_set(0)
    stdscr.nodelay(True)

    state = {
        "idx": 0,
        "percent": 0,
        "status": "Starting...",
        "done": False,
        "result": None,
    }

    def update_cb(idx, percent, status):
        state["idx"] = idx
        state["percent"] = int(percent)
        state["status"] = status

    def runner():
        try:
            state["result"] = worker_fn(update_cb)
        except Exception as e:
            state["result"] = f"ERROR: {e}"
        state["done"] = True

    th = threading.Thread(target=runner, daemon=True)
    th.start()

    spin = ["|", "/", "-", "\\"]
    spin_i = 0

    while not state["done"]:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        draw_center(stdscr, 1, title, cp(1) | curses.A_BOLD, width=w)

        # Current item
        if 0 <= state["idx"] < len(items):
            name = items[state["idx"]]
        else:
            name = ""
        if len(name) > w - 6:
            name = name[:w - 9] + "..."
        draw_center(stdscr, 3, name, cp(5), width=w)

        # Progress bar
        bar_w = min(w - 20, 40)
        filled = int(bar_w * state["percent"] / 100)
        bar = "[" + "#" * filled + "." * (bar_w - filled) + "]"
        pct_str = f"{state['percent']:3d}%"
        line = f"{spin[spin_i % len(spin)]}  {bar}  {pct_str}"
        draw_center(stdscr, 5, line, cp(2) | curses.A_BOLD, width=w)

        # Status
        draw_center(stdscr, 7, state["status"], cp(7), width=w)

        # Footer
        draw_center(stdscr, h - 2, "Press Ctrl+C to abort", cp(3), width=w)

        stdscr.refresh()
        spin_i += 1

        # Check for Ctrl+C (nodelay)
        try:
            k = stdscr.getch()
            if k == 3:  # Ctrl+C
                return None
        except curses.error:
            pass

        time.sleep(0.08)

    # Final state
    stdscr.clear()
    draw_center(stdscr, 3, title, cp(1) | curses.A_BOLD, width=w)
    draw_center(stdscr, 5, "DONE", cp(2) | curses.A_BOLD, width=w)
    stdscr.refresh()
    time.sleep(0.5)

    return state["result"]


# ==================================================
#   PROCESS (uses curses progress)
# ==================================================
def process_curses(stdscr, input_folder, output_folder, videos, audios, images, preset_key):
    output_folder.mkdir(parents=True, exist_ok=True)
    tasks = ([("video", v) for v in videos]
             + [("audio", a) for a in audios]
             + [("image", i) for i in images])

    if not tasks:
        return

    results = {"done": 0, "skipped": 0, "failed": 0, "old": 0, "new": 0}

    def worker(update_cb):
        for i, (kind, src) in enumerate(tasks):
            rel = src.relative_to(input_folder) if src.is_relative_to(input_folder) else Path(src.name)
            dst = output_folder / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            old_size = src.stat().st_size

            if dst.exists():
                update_cb(i, 100, f"[skip] {src.name}")
                results["old"] += old_size
                results["new"] += dst.stat().st_size
                continue

            if kind == "audio" and dst.suffix.lower() not in {".mp3", ".m4a", ".aac"}:
                dst = dst.with_suffix(".mp3")
            if kind == "image" and dst.suffix.lower() in {".png", ".bmp", ".tiff", ".tif", ".heic"}:
                dst = dst.with_suffix(".jpg")

            def progress(p):
                update_cb(i, p, f"{kind}: {src.name}")

            try:
                if kind == "video":
                    ok = smart_compress_video(src, dst, preset_key, progress)
                elif kind == "audio":
                    ok = smart_compress_audio(src, dst, preset_key, progress)
                else:
                    ok, dst = smart_compress_image(src, dst, preset_key, progress)
            except Exception:
                ok = False

            if ok and dst.exists():
                new_size = dst.stat().st_size
                results["done"] += 1
                results["old"] += old_size
                results["new"] += new_size
            else:
                try:
                    if dst.exists():
                        dst.unlink()
                    shutil.copy2(src, dst)
                except Exception:
                    pass
                results["skipped"] += 1
                results["old"] += old_size
                results["new"] += old_size

        return results

    item_names = [t[1].name for t in tasks]
    curses_progress(stdscr, "Compressing...", item_names, worker)

    # Show report
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    box_w = min(w - 4, 60)
    box_left = (w - box_w) // 2
    box_top = max(1, h // 2 - 8)

    draw_box(stdscr, box_top, box_left, 3, box_w, cp(1))
    draw_center(stdscr, box_top + 1, "REPORT", cp(1) | curses.A_BOLD, width=w)

    row = box_top + 4
    def line(text, color=cp(5)):
        nonlocal row
        draw_center(stdscr, row, text, color, width=w)
        row += 1

    line(f"Compressed : {results['done']}", cp(2))
    line(f"Kept orig  : {results['skipped']}", cp(3))
    line(f"Failed     : {results['failed']}", cp(4))

    if results["old"]:
        saved = results["old"] - results["new"]
        pct = saved / results["old"] * 100
        line(f"Original   : {human_size(results['old'])}")
        line(f"New        : {human_size(results['new'])}")
        line(f"Saved      : {human_size(saved)}  ({pct:+.1f}%)",
             cp(2) if saved > 0 else cp(3))

    row += 1
    line(f"Output: {str(output_folder)}", cp(2))

    draw_center(stdscr, h - 2, "Press any key to continue", cp(7), width=w)
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


# ==================================================
#   MAIN CURSES APP
# ==================================================
def curses_main(stdscr):
    init_colors()
    curses.curs_set(0)
    stdscr.keypad(True)

    # ---- MAIN MENU LOOP ----
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Splash banner (top)
        draw_center(stdscr, 0, "=" * min(w - 2, 50), cp(1), width=w)
        draw_center(stdscr, 1, "ULTRA COMPRESSOR", cp(1) | curses.A_BOLD, width=w)
        draw_center(stdscr, 2, f"by {AUTHOR}  |  v{VERSION}", cp(3), width=w)
        draw_center(stdscr, 3, "=" * min(w - 2, 50), cp(1), width=w)
        stdscr.refresh()

        options = [
            "1. Compress specific files",
            "2. Compress FULL FOLDER",
            "3. Extract AUDIO from videos (VIDEO to MP3)",
            "4. Quit",
        ]

        idx = curses_menu(stdscr, "MAIN MENU", options,
                          subtitle="Compress video, audio, and images")
        if idx is None or idx == 3:
            break

        # ---- INPUT FOLDER ----
        raw = curses_input(stdscr, "INPUT FOLDER",
                           "Path:", default=".", allow_empty=False)
        if raw is None or raw.lower() == "q":
            continue

        raw = raw.strip('"').strip("'")
        folder = Path(os.path.expanduser(raw))
        if not folder.exists() or not folder.is_dir():
            # Show error briefly
            stdscr.clear()
            draw_center(stdscr, 3, f"Not a folder: {folder}", cp(4), width=w)
            draw_center(stdscr, 5, "Press any key to return...", cp(7), width=w)
            stdscr.refresh()
            stdscr.nodelay(False)
            stdscr.getch()
            continue

        # ---- ACTION ----
        if idx == 1:  # full folder
            videos, audios, images = scan_folder(folder)
            total = len(videos) + len(audios) + len(images)
            if total == 0:
                stdscr.clear()
                draw_center(stdscr, 3, "No media files found!", cp(4), width=w)
                draw_center(stdscr, 5, "Press any key...", cp(7), width=w)
                stdscr.refresh()
                stdscr.nodelay(False)
                stdscr.getch()
                continue

            # Choose preset
            preset_key = curses_choose_preset(stdscr)
            if preset_key is None:
                continue

            # Output folder
            default_out = f"Compressed_{folder.resolve().name or 'output'}"
            out_raw = curses_input(stdscr, "OUTPUT FOLDER",
                                   "Name:", default=default_out, allow_empty=False)
            if out_raw is None:
                continue
            out_folder = Path(out_raw)
            if not out_folder.is_absolute():
                out_folder = folder.parent / out_raw

            process_curses(stdscr, folder, out_folder, videos, audios, images, preset_key)

        elif idx == 2:  # video -> audio
            videos, _, _ = scan_folder(folder)
            if not videos:
                stdscr.clear()
                draw_center(stdscr, 3, "No video files found!", cp(4), width=w)
                draw_center(stdscr, 5, "Press any key...", cp(7), width=w)
                stdscr.refresh()
                stdscr.nodelay(False)
                stdscr.getch()
                continue

            default_out = f"Extracted_{folder.resolve().name or 'audio'}"
            out_raw = curses_input(stdscr, "OUTPUT FOLDER",
                                   "Name:", default=default_out, allow_empty=False)
            if out_raw is None:
                continue
            out_folder = Path(out_raw)
            if not out_folder.is_absolute():
                out_folder = folder.parent / out_raw

            # Extract all
            tasks = [(v, out_folder / (v.stem + ".mp3")) for v in videos]
            out_folder.mkdir(parents=True, exist_ok=True)

            def worker(update_cb):
                done = 0
                for i, (src, dst) in enumerate(tasks):
                    def prog(p):
                        update_cb(i, p, f"Extracting: {src.name}")
                    extract_audio_from_video(src, dst, prog)
                    if dst.exists():
                        done += 1
                return done

            item_names = [v.name for v in videos]
            curses_progress(stdscr, "Extracting audio...", item_names, worker)

            stdscr.clear()
            draw_center(stdscr, 3, f"Extracted {len(videos)} file(s)", cp(2), width=w)
            draw_center(stdscr, 5, "Press any key...", cp(7), width=w)
            stdscr.refresh()
            stdscr.nodelay(False)
            stdscr.getch()

        else:  # idx == 0: specific files
            videos, audios, images = scan_folder(folder)
            if not videos and not audios and not images:
                stdscr.clear()
                draw_center(stdscr, 3, "No media files found!", cp(4), width=w)
                draw_center(stdscr, 5, "Press any key...", cp(7), width=w)
                stdscr.refresh()
                stdscr.nodelay(False)
                stdscr.getch()
                continue

            # Build options
            all_files = ([("video", v) for v in videos]
                         + [("audio", a) for a in audios]
                         + [("image", i) for i in images])

            options_list = []
            for kind, f in all_files:
                tag = {"video": "[V]", "audio": "[A]", "image": "[I]"}[kind]
                options_list.append(f"{tag} {f.name[:40]:<40} {human_size(f.stat().st_size):>10}")

            selected = curses_multi_select(stdscr, "SELECT FILES", options_list)
            if not selected:
                continue

            sel_v, sel_a, sel_i = [], [], []
            for i in selected:
                kind, f = all_files[i]
                if kind == "video":
                    sel_v.append(f)
                elif kind == "audio":
                    sel_a.append(f)
                else:
                    sel_i.append(f)

            preset_key = curses_choose_preset(stdscr)
            if preset_key is None:
                continue

            default_out = f"Compressed_{folder.resolve().name or 'output'}"
            out_raw = curses_input(stdscr, "OUTPUT FOLDER",
                                   "Name:", default=default_out, allow_empty=False)
            if out_raw is None:
                continue
            out_folder = Path(out_raw)
            if not out_folder.is_absolute():
                out_folder = folder.parent / out_raw

            process_curses(stdscr, folder, out_folder, sel_v, sel_a, sel_i, preset_key)

    # Exit
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    draw_center(stdscr, h // 2, f"Bye! - [Hope You Like It]", cp(1) | curses.A_BOLD, width=w)
    stdscr.refresh()
    time.sleep(1.4)


# ==================================================
#   PRESET CHOOSER (curses)
# ==================================================
def curses_choose_preset(stdscr):
    ram = get_total_ram_mb()
    free = get_free_ram_mb()
    sug, reason = suggest_preset()

    options = []
    keys = []
    for k in PRESET_ORDER:
        p = PRESETS[k]
        min_ram = p["min_ram_mb"]
        blocked = ram < min_ram
        line = f"{k}. {p['label']:<12} {p['desc']}"
        if blocked:
            line += f"  [needs {min_ram}MB]"
        if k == sug:
            line += "  *"
        options.append(line)
        keys.append(k)

    subtitle = f"RAM: {ram} MB total, {free} MB free  |  Suggested: {sug}"
    idx = curses_menu(stdscr, "CHOOSE PRESET", options, subtitle=subtitle)
    if idx is None:
        return None
    return keys[idx]


# ==================================================
#   MULTI-SELECT (space to toggle, enter to confirm)
# ==================================================
def curses_multi_select(stdscr, title, options):
    curses.curs_set(0)
    selected = 0
    n = len(options)
    checked = set()
    scroll = 0  # top visible index

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        draw_center(stdscr, 0, title, cp(1) | curses.A_BOLD, width=w)
        draw_center(stdscr, 1, "Up/Down: Navigate  |  Space: Toggle  |  a: All  |  Enter: Confirm  |  q: Cancel",
                    cp(7), width=w)

        visible_start = max(0, selected - (h - 8) // 2)
        visible_end = min(n, visible_start + (h - 7))

        for i in range(visible_start, visible_end):
            row = 3 + (i - visible_start)
            mark = "[x]" if i in checked else "[ ]"
            if i == selected:
                attr = cp(6) | curses.A_BOLD | curses.A_REVERSE
            else:
                attr = cp(5)
            text = f"  {mark} {options[i]}"
            try:
                stdscr.addstr(row, 2, text[:w - 3], attr)
            except curses.error:
                pass

        # Footer
        footer = f"Selected: {len(checked)} / {n}   |   q: cancel   Enter: confirm"
        draw_center(stdscr, h - 2, footer, cp(2) | curses.A_BOLD, width=w)
        stdscr.refresh()

        k = stdscr.getch()
        if k == curses.KEY_UP:
            selected = (selected - 1) % n
        elif k == curses.KEY_DOWN:
            selected = (selected + 1) % n
        elif k == ord(" "):
            if selected in checked:
                checked.remove(selected)
            else:
                checked.add(selected)
            # auto-advance
            selected = (selected + 1) % n
        elif k in (10, 13, curses.KEY_ENTER):
            return sorted(checked)
        elif k in (ord("q"), 27):
            return []
        elif k == ord("a"):
            if len(checked) == n:
                checked.clear()
            else:
                checked = set(range(n))
        elif k == curses.KEY_HOME:
            selected = 0
        elif k == curses.KEY_END:
            selected = n - 1


# ==================================================
#   ENTRY POINT
# ==================================================
def main():
    try:
        curses.wrapper(curses_main)
    except KeyboardInterrupt:
        print(f"\nBye! - {AUTHOR}")
    except Exception as e:
        print(f"Fatal: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
