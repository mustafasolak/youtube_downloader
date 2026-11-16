#!/usr/bin/env python3
"""YouTube Downloader - GUI + CLI. Kullanim: python ytdl.py --gui"""

import os
import sys
import shutil
import threading
import queue
import argparse

import yt_dlp
YoutubeDL = yt_dlp.YoutubeDL

APP_TITLE = "YouTube Downloader"
FFMPEG_OK = shutil.which("ffmpeg") is not None

FORMATS = {
    "best":  {"label": "En iyi kalite (video+ses)", "fmt": "bv*+ba/b"},
    "2160":  {"label": "4K / 2160p",               "fmt": "bv*[height<=2160]+ba/b[height<=2160]"},
    "1440":  {"label": "1440p",                    "fmt": "bv*[height<=1440]+ba/b[height<=1440]"},
    "1080":  {"label": "1080p",                    "fmt": "bv*[height<=1080]+ba/b[height<=1080]"},
    "720":   {"label": "720p",                     "fmt": "bv*[height<=720]+ba/b[height<=720]"},
    "480":   {"label": "480p",                     "fmt": "bv*[height<=480]+ba/b[height<=480]"},
    "audio": {"label": "Sadece ses (MP3 192k)",    "fmt": "ba/b"},
}


class _Logger:
    def __init__(self, hook):
        self.hook = hook

    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.hook(msg)

    def info(self, msg):
        self.hook(msg)

    def warning(self, msg):
        self.hook("UYARI: " + msg)

    def error(self, msg):
        self.hook("HATA: " + msg)


def make_opts(outdir, mode, progress_hook=None, log_hook=None):
    os.makedirs(outdir, exist_ok=True)
    spec = FORMATS.get(mode, FORMATS["best"])
    opts = {
        "format": spec["fmt"],
        "outtmpl": os.path.join(outdir, "%(title).150B [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "ignoreerrors": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "socket_timeout": 30,
        "remote_components": ["ejs:github"],
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
    }
    if mode == "audio":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["merge_output_format"] = "mp4"
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if log_hook:
        opts["logger"] = _Logger(log_hook)
    return opts


def run_download(urls, outdir, mode, progress_hook=None, log_hook=None):
    opts = make_opts(outdir, mode, progress_hook, log_hook)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download(urls)


def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("640x460")
    root.minsize(560, 400)

    q = queue.Queue()
    state = {"running": False}

    top = ttk.Frame(root, padding=10)
    top.pack(fill="x")

    ttk.Label(top, text="Video / playlist URL'leri (her satira bir tane):").pack(anchor="w")
    url_box = tk.Text(top, height=5, wrap="none")
    url_box.pack(fill="x", pady=(4, 8))

    row = ttk.Frame(top)
    row.pack(fill="x")

    ttk.Label(row, text="Kalite:").pack(side="left")
    mode_cb = ttk.Combobox(
        row, state="readonly", width=28,
        values=[f"{k} - {v['label']}" for k, v in FORMATS.items()],
    )
    mode_cb.set("best - " + FORMATS["best"]["label"])
    mode_cb.pack(side="left", padx=(6, 16))

    ttk.Label(row, text="Klasor:").pack(side="left")
    dir_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
    ttk.Entry(row, textvariable=dir_var, width=22).pack(side="left", padx=(6, 4))

    def pick_dir():
        d = filedialog.askdirectory(initialdir=dir_var.get())
        if d:
            dir_var.set(d)

    ttk.Button(row, text="Sec", command=pick_dir).pack(side="left")

    bar = ttk.Progressbar(root, mode="determinate", maximum=100)
    bar.pack(fill="x", padx=10, pady=(10, 4))

    status = ttk.Label(
        root,
        text="Hazir." + ("" if FFMPEG_OK else "  (ffmpeg yok: birlestirme/MP3 calismaz)"),
    )
    status.pack(anchor="w", padx=10)

    log = tk.Text(root, height=10, state="disabled", wrap="word")
    log.pack(fill="both", expand=True, padx=10, pady=(6, 6))

    def log_msg(msg):
        log.configure(state="normal")
        log.insert("end", str(msg).rstrip() + "\n")
        log.see("end")
        log.configure(state="disabled")

    def progress_hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            if total:
                pct = done * 100 / total
                q.put(("progress", pct))
                q.put(("status", f"%{pct:.1f}  {d.get('_speed_str','').strip()}  {d.get('_eta_str','').strip()}"))
        elif d.get("status") == "finished":
            q.put(("status", "Isleniyor (birlestirme/donusturme)..."))

    def worker(urls, outdir, mode):
        try:
            run_download(urls, outdir, mode, progress_hook, lambda m: q.put(("log", m)))
            q.put(("done", f"Bitti. Klasor: {outdir}"))
        except Exception as e:
            q.put(("done", f"Hata: {e}"))

    def pump():
        try:
            while True:
                kind, payload = q.get_nowait()
                if kind == "progress":
                    bar["value"] = payload
                elif kind == "status":
                    status.configure(text=payload)
                elif kind == "log":
                    log_msg(payload)
                elif kind == "done":
                    status.configure(text=payload)
                    state["running"] = False
                    start_btn.configure(state="normal")
                    bar["value"] = 0
        except queue.Empty:
            pass
        root.after(120, pump)

    def start():
        if state["running"]:
            return
        urls = [u.strip() for u in url_box.get("1.0", "end").splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning(APP_TITLE, "En az bir URL gir.")
            return
        mode = mode_cb.get().split(" - ")[0]
        if mode not in FORMATS:
            mode = "best"
        state["running"] = True
        start_btn.configure(state="disabled")
        log_msg("--- basladi ---")
        threading.Thread(target=worker, args=(urls, dir_var.get(), mode), daemon=True).start()

    start_btn = ttk.Button(root, text="Indir", command=start)
    start_btn.pack(fill="x", padx=10, pady=(0, 10))

    pump()
    root.mainloop()


def cli():
    p = argparse.ArgumentParser(description="YouTube Downloader")
    p.add_argument("urls", nargs="*", help="Indirilecek URL(ler)")
    p.add_argument("-o", "--out", default="indirilenler", help="Cikti klasoru")
    p.add_argument("-f", "--format", default="best", choices=FORMATS.keys(), help="Kalite")
    p.add_argument("--gui", action="store_true", help="GUI ac")
    a = p.parse_args()

    if a.gui or not a.urls:
        gui()
        return

    if not FFMPEG_OK and a.format != "best":
        print("UYARI: ffmpeg yok, birlestirme/MP3 sorun cikarabilir.\n")

    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            if total:
                pct = done * 100 / total
                sys.stdout.write(f"\r%{pct:5.1f}  {d.get('_speed_str','').strip()} {d.get('_eta_str','').strip()}   ")
                sys.stdout.flush()
        elif d.get("status") == "finished":
            print("\nIsleniyor...")

    try:
        run_download(a.urls, a.out, a.format, hook, print)
        print(f"\nBitti -> {os.path.abspath(a.out)}")
    except KeyboardInterrupt:
        print("\nIptal.")
    except Exception as e:
        print(f"\nHata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
