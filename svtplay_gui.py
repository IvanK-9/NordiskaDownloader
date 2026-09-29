"""
NordiskaDownloader v1.3
Desktop GUI (customtkinter) wrapper around the svtplay-dl command-line tool.
Setup: pip install -r requirements.txt  |  Run: python svtplay_gui.py
"""

import customtkinter as ctk
import subprocess
import threading
import os
import sys
import re
import shutil
from pathlib import Path
from tkinter import StringVar, filedialog
from PIL import Image, ImageDraw

APP_NAME    = "NordiskaDownloader"
APP_VERSION = "v1.3"

SE_BLUE   = "#006AA7"
SE_YELLOW = "#FECC02"
BG_DARK   = "#0A0E14"
BG_CARD   = "#111827"
TEXT_DIM  = "#4A5568"
TEXT_MID  = "#8899AA"
TEXT_MAIN = "#D0DCE8"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

QUALITY_OPTIONS = {
    "Top  1080p+":  ["--resolution", ">=1080"],
    "Medium  480p": ["--resolution", "<720"],
}


def find_svtplay_dl() -> list:
    """
    Возвращает команду для запуска svtplay-dl.
    Приоритет:
      1. svtplay-dl.exe рядом со скриптом/exe
      2. python.exe из venv рядом со скриптом  -> python -m svtplay_dl
      3. системный PATH
    """
    # 1. svtplay-dl.exe рядом с нашим файлом
    for name in ["svtplay-dl.exe", "svtplay-dl"]:
        p = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(p):
            return [p]

    # 2. venv рядом со скриптом (для разработки)
    venv_python = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")
    if os.path.isfile(venv_python):
        return [venv_python, "-m", "svtplay_dl"]

    # 3. PATH
    found = shutil.which("svtplay-dl")
    if found:
        return [found]

    # 4. python в PATH + модуль
    py = shutil.which("python") or shutil.which("python3")
    if py:
        return [py, "-m", "svtplay_dl"]

    return ["svtplay-dl"]  # last resort


def find_ffmpeg() -> str:
    for name in ["ffmpeg.exe", "ffmpeg"]:
        p = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(p):
            return p
    return shutil.which("ffmpeg") or ""


# ── Logo ──────────────────────────────────────────────────────────────────────
def make_logo(size=48) -> ctk.CTkImage:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size-1, size-1], fill="#006AA7")
    cx = size // 2
    bar = max(3, size // 9)
    vx = int(size * 0.38)
    d.rectangle([bar, cx - bar, size - bar, cx + bar], fill="#FECC02")
    d.rectangle([vx - bar, bar, vx + bar, size - bar], fill="#FECC02")
    ax, ay = int(size * 0.58), int(size * 0.52)
    aw = int(size * 0.30)
    ah = int(size * 0.30)
    sw = max(2, size // 16)
    d.rectangle([ax + aw//2 - sw, ay, ax + aw//2 + sw, ay + ah - sw*2], fill="white")
    d.polygon([ax, ay+ah-sw*3, ax+aw, ay+ah-sw*3, ax+aw//2, ay+ah], fill="white")
    d.rectangle([ax, ay+ah, ax+aw, ay+ah+sw*2], fill="white")
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


# ── App ───────────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("680x620")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self._process = None
        self._build_ui()

    def _card(self, title: str, row: int):
        frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(6, 0))
        ctk.CTkLabel(frame, text=title.upper(),
                     font=ctk.CTkFont("Trebuchet MS", 10, "bold"),
                     text_color=SE_YELLOW).pack(anchor="w", padx=16, pady=(12, 2))
        self._last_card = frame

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color="#040810")
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="", image=make_logo(46)
                     ).grid(row=0, column=0, padx=(18, 12), pady=14)
        tf = ctk.CTkFrame(hdr, fg_color="transparent")
        tf.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(tf, text=APP_NAME,
                     font=ctk.CTkFont("Trebuchet MS", 22, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(tf, text="Nordic streaming downloader  ·  powered by svtplay-dl",
                     font=ctk.CTkFont("Trebuchet MS", 10),
                     text_color=TEXT_DIM).pack(anchor="w")
        ctk.CTkLabel(hdr, text=APP_VERSION,
                     font=ctk.CTkFont("Consolas", 10),
                     text_color="#263347").grid(row=0, column=2, padx=18)
        ctk.CTkFrame(self, height=2, fg_color=SE_BLUE, corner_radius=0
                     ).grid(row=1, column=0, sticky="ew")

        # URL
        self._card("URL", row=2)
        ui = ctk.CTkFrame(self._last_card, fg_color="transparent")
        ui.pack(fill="x", padx=16, pady=(6, 14))
        ui.grid_columnconfigure(0, weight=1)
        self.url_var = StringVar()
        ctk.CTkEntry(ui, textvariable=self.url_var, height=42,
                     placeholder_text="https://www.svtplay.se/video/...   or   tv4play.se/...",
                     font=ctk.CTkFont("Consolas", 12),
                     fg_color="#0D1520", border_color=SE_BLUE, border_width=1,
                     text_color=TEXT_MAIN).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(ui, text="Paste", width=76, height=42,
                      fg_color="#0D2035", hover_color=SE_BLUE, text_color=SE_YELLOW,
                      command=self._paste).grid(row=0, column=1, padx=(8, 0))

        # Save to
        self._card("Save to", row=3)
        di = ctk.CTkFrame(self._last_card, fg_color="transparent")
        di.pack(fill="x", padx=16, pady=(6, 14))
        di.grid_columnconfigure(0, weight=1)
        self.dir_var = StringVar(value=str(Path.home() / "Downloads"))
        ctk.CTkEntry(di, textvariable=self.dir_var, height=38,
                     font=ctk.CTkFont("Consolas", 11),
                     fg_color="#0D1520", border_color="#1E2A3A", border_width=1,
                     text_color=TEXT_MID).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(di, text="Browse", width=80, height=38,
                      fg_color="#0D2035", hover_color=SE_BLUE, text_color=SE_YELLOW,
                      command=self._browse).grid(row=0, column=1, padx=(8, 0))

        # Quality + Token
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=4, column=0, sticky="ew", padx=16)
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_columnconfigure(1, weight=1)

        qc = ctk.CTkFrame(mid, fg_color=BG_CARD, corner_radius=12)
        qc.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=8)
        ctk.CTkLabel(qc, text="QUALITY",
                     font=ctk.CTkFont("Trebuchet MS", 10, "bold"),
                     text_color=SE_YELLOW).pack(anchor="w", padx=16, pady=(12, 4))
        self.quality_var = StringVar(value=list(QUALITY_OPTIONS.keys())[0])
        for label in QUALITY_OPTIONS:
            ctk.CTkRadioButton(qc, text=label, value=label,
                               variable=self.quality_var,
                               font=ctk.CTkFont("Trebuchet MS", 13),
                               text_color=TEXT_MAIN,
                               fg_color=SE_BLUE, hover_color="#0082CC"
                               ).pack(anchor="w", padx=16, pady=3)
        ctk.CTkFrame(qc, height=12, fg_color="transparent").pack()

        tc = ctk.CTkFrame(mid, fg_color=BG_CARD, corner_radius=12)
        tc.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=8)
        tc.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tc, text="TOKEN  (tv4play.se only)",
                     font=ctk.CTkFont("Trebuchet MS", 10, "bold"),
                     text_color=SE_YELLOW).grid(row=0, column=0, columnspan=2,
                                                 sticky="w", padx=16, pady=(12, 4))
        self.token_var = StringVar()
        self._tok_entry = ctk.CTkEntry(tc, textvariable=self.token_var,
                                       height=36, show="*",
                                       placeholder_text="ey...",
                                       font=ctk.CTkFont("Consolas", 11),
                                       fg_color="#0D1520", border_color="#1E2A3A",
                                       border_width=1, text_color=TEXT_MID)
        self._tok_entry.grid(row=1, column=0, sticky="ew", padx=(16, 6), pady=(0, 4))
        ctk.CTkButton(tc, text="👁", width=36, height=36,
                      fg_color="#0D2035", hover_color=SE_BLUE,
                      command=self._toggle_token).grid(row=1, column=1, padx=(0, 16))
        ctk.CTkLabel(tc,
                     text="F12 → Console on tv4play.se\ndocument.cookie.split(';')"
                          ".find(r=>r.includes('tv4-refresh-token'))",
                     font=ctk.CTkFont("Consolas", 9), text_color=TEXT_DIM,
                     justify="left").grid(row=2, column=0, columnspan=2,
                                          sticky="w", padx=16, pady=(0, 12))

        # Buttons
        br = ctk.CTkFrame(self, fg_color="transparent")
        br.grid(row=5, column=0, sticky="ew", padx=16, pady=(4, 6))
        self.dl_btn = ctk.CTkButton(br, text="⬇   Download", width=180, height=50,
                                    font=ctk.CTkFont("Trebuchet MS", 16, "bold"),
                                    fg_color=SE_BLUE, hover_color="#0082CC",
                                    text_color="white", corner_radius=10,
                                    command=self._start)
        self.dl_btn.pack(side="left")
        self.stop_btn = ctk.CTkButton(br, text="■  Stop", width=100, height=50,
                                      font=ctk.CTkFont("Trebuchet MS", 14),
                                      fg_color="#3D0000", hover_color="#7F1D1D",
                                      text_color="#FF6B6B", corner_radius=10,
                                      state="disabled", command=self._stop)
        self.stop_btn.pack(side="left", padx=10)
        self.status_lbl = ctk.CTkLabel(br, text="Ready",
                                       font=ctk.CTkFont("Trebuchet MS", 13),
                                       text_color=TEXT_DIM)
        self.status_lbl.pack(side="left", padx=14)

        # Progress
        pc = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        pc.grid(row=6, column=0, sticky="ew", padx=16, pady=6)
        pc.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pc, text="PROGRESS",
                     font=ctk.CTkFont("Trebuchet MS", 10, "bold"),
                     text_color=SE_YELLOW).grid(row=0, column=0, sticky="w",
                                                 padx=16, pady=(12, 4))
        self.progress = ctk.CTkProgressBar(pc, height=24, corner_radius=8,
                                           fg_color="#0A1525", progress_color=SE_BLUE)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        self.pct_lbl = ctk.CTkLabel(pc, text="0%",
                                    font=ctk.CTkFont("Consolas", 16, "bold"),
                                    text_color=SE_YELLOW, width=58)
        self.pct_lbl.grid(row=1, column=1, padx=(6, 16))
        self.eta_lbl = ctk.CTkLabel(pc, text="Waiting…",
                                    font=ctk.CTkFont("Trebuchet MS", 11),
                                    text_color=TEXT_DIM)
        self.eta_lbl.grid(row=2, column=0, columnspan=2,
                          sticky="w", padx=16, pady=(0, 12))

        # Log
        self.log = ctk.CTkTextbox(self, height=96,
                                  font=ctk.CTkFont("Consolas", 10),
                                  text_color="#4A6080", fg_color="#050A10",
                                  border_color="#0D1A28", border_width=1,
                                  wrap="word", corner_radius=10)
        self.log.grid(row=7, column=0, sticky="ew", padx=16, pady=(4, 16))
        self.log.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _paste(self):
        try:
            self.url_var.set(self.clipboard_get())
        except Exception:
            pass

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(d)

    def _toggle_token(self):
        self._tok_entry.configure(
            show="" if self._tok_entry.cget("show") == "*" else "*")

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, text, color=TEXT_DIM):
        self.status_lbl.configure(text=text, text_color=color)

    _POS_RE = re.compile(r"\[\s*(\d+)/(\d+)\]")
    _ETA_RE = re.compile(r"ETA:\s*([\w:]+)")

    def _parse_progress(self, line):
        # формат svtplay-dl: [099/500][=====.....] ETA: 13:36:59
        m = self._POS_RE.search(line)
        if m and int(m.group(2)) > 0:
            if self.progress.cget("mode") != "determinate":
                self.progress.stop()
                self.progress.configure(mode="determinate")
            pct = int(int(m.group(1)) * 100 / int(m.group(2)))
            self.progress.set(pct / 100)
            self.pct_lbl.configure(text=f"{pct}%")
            e = self._ETA_RE.search(line)
            if e:
                self.eta_lbl.configure(text=f"  ETA {e.group(1)}")

    def _build_cmd(self):
        url = self.url_var.get().strip()
        if not url:
            return None, "Please enter a URL."

        cmd = find_svtplay_dl()          # правильная команда запуска
        cmd.extend(QUALITY_OPTIONS.get(self.quality_var.get(), []))

        out = self.dir_var.get().strip()
        if out:
            cmd += ["-o", out]

        tok = self.token_var.get().strip()
        if tok:
            cmd += ["--token", tok]

        cmd += ["--output-format", "mp4"]

        cmd.append(url)
        return cmd, None

    # ── Download ──────────────────────────────────────────────────────────────
    def _start(self):
        cmd, err = self._build_cmd()
        if err:
            self._append_log(f"[ERROR] {err}\n")
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.progress.set(0)
        self.pct_lbl.configure(text="0%")
        self.eta_lbl.configure(text="Starting…")
        self.dl_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.configure(mode="indeterminate", progress_color=SE_YELLOW)
        self.progress.start()
        self._set_status("Downloading…", SE_YELLOW)
        svt_cmd = find_svtplay_dl()
        self._append_log(f"svtplay-dl: {svt_cmd[0]}\n")
        ffmpeg_path = find_ffmpeg()
        self._append_log(f"ffmpeg:     {ffmpeg_path or 'NOT FOUND - audio and video will stay separate!'}\n\n")
        self._append_log("CMD: " + " ".join(cmd) + "\n\n")

        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    def _run(self, cmd):
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            env = os.environ.copy()
            ff = find_ffmpeg()
            if ff:
                env["PATH"] = os.path.dirname(ff) + os.pathsep + env.get("PATH", "")
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=flags, env=env)
            for line in self._process.stdout:
                self.after(0, self._append_log, line)
                self.after(0, self._parse_progress, line)
            self.after(0, self._done, self._process.wait() == 0)
        except FileNotFoundError as e:
            self.after(0, self._append_log,
                       f"[ERROR] Не найден: {e}\n"
                       "Убедись что svtplay-dl установлен: pip install svtplay-dl\n")
            self.after(0, self._done, False)

    def _done(self, ok):
        self.progress.stop()
        self.progress.configure(mode="determinate",
                                progress_color=SE_BLUE if ok else "#7F1D1D")
        self.progress.set(1.0 if ok else 0.3)
        self.pct_lbl.configure(text="100%" if ok else "—")
        self.dl_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._process = None
        if ok:
            self._set_status("Done ✓", "#4ADE80")
            self.eta_lbl.configure(text="  ✓  Audio + video merged to .mp4")
        else:
            self._set_status("Failed ✗", "#FF6B6B")
            self.eta_lbl.configure(text="  ✗  Смотри лог выше")

    def _stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._append_log("[Stopped by user]\n")


if __name__ == "__main__":
    app = App()
    app.mainloop()
