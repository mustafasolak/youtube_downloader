#!/usr/bin/env python3
"""Toplu indirici - koyu tema, satir bazli ilerleme.
Kullanim: python uygulama.py
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp
import ytdl

ARCHIVE = os.path.expanduser("~/.ytdl_archive.txt")
DEFAULT_LIST = "https://www.youtube.com/watch?list=PLacUFbb-E-LQ"

BG = "#0f0f10"
PANEL = "#17171a"
LINE = "#26262a"
FG = "#eaeaea"
MUTED = "#8a8a8f"
ACCENT = "#4ea3ff"
GREEN = "#2ecc71"
RED = "#ff5c5c"


def parse_urls(text):
    return [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]


def fmt_dur(sec):
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return ""
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.jobs = queue.Queue()
        self.items = []
        self.seen = set()
        self.pending = 0
        self.ok = []
        self.fail = []
        self.running = False
        self.stop_flag = threading.Event()

        root.title("Video İndirici")
        root.geometry("880x820")
        root.minsize(760, 700)
        root.configure(bg=BG)

        self.style()

        outer = tk.Frame(root, bg=BG, padx=16, pady=14)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="Video İndirici", bg=BG, fg=FG,
                 font=("Helvetica Neue", 18, "bold")).pack(anchor="w")
        tk.Label(outer, text="Playlist ya da video linkleri, her satıra bir tane",
                 bg=BG, fg=MUTED, font=("Helvetica Neue", 11)).pack(anchor="w", pady=(2, 12))

        # --- liste ---
        tk.Label(outer, text="Liste", bg=BG, fg=MUTED, font=("Helvetica Neue", 10)).pack(anchor="w")
        self.text = tk.Text(outer, height=5, bg=PANEL, fg=FG, insertbackground=FG,
                            relief="flat", highlightthickness=1, highlightbackground=LINE,
                            highlightcolor=ACCENT, font=("Menlo", 11), padx=10, pady=8, undo=True)
        self.text.pack(fill="x", pady=(4, 6))
        self.text.insert("1.0", DEFAULT_LIST)

        file_row = tk.Frame(outer, bg=BG)
        file_row.pack(fill="x", pady=(0, 10))

        self.path_var = tk.StringVar()
        tk.Entry(file_row, textvariable=self.path_var, bg=PANEL, fg=FG, insertbackground=FG,
                 relief="flat", highlightthickness=1, highlightbackground=LINE,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True, ipady=5)
        for txt, cmd in (("Gözat", self.pick_list), ("Yükle", self.load_file), ("Kaydet", self.save_file)):
            ttk.Button(file_row, text=txt, style="Ghost.TButton", command=cmd).pack(side="left", padx=(6, 0))

        # --- ayarlar ---
        row = tk.Frame(outer, bg=BG)
        row.pack(fill="x", pady=(0, 10))

        tk.Label(row, text="Kalite", bg=BG, fg=MUTED, font=("Helvetica Neue", 10)).pack(side="left")
        self.mode_cb = ttk.Combobox(row, state="readonly", width=24,
                                    values=[f"{k} - {v['label']}" for k, v in ytdl.FORMATS.items()])
        self.mode_cb.set("best - " + ytdl.FORMATS["best"]["label"])
        self.mode_cb.pack(side="left", padx=(6, 18))

        tk.Label(row, text="Klasör", bg=BG, fg=MUTED, font=("Helvetica Neue", 10)).pack(side="left")
        self.dir_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        tk.Entry(row, textvariable=self.dir_var, width=24, bg=PANEL, fg=FG, insertbackground=FG,
                 relief="flat", highlightthickness=1, highlightbackground=LINE,
                 highlightcolor=ACCENT).pack(side="left", padx=(6, 6), ipady=5)
        ttk.Button(row, text="Seç", style="Ghost.TButton", command=self.pick_dir).pack(side="left")

        # --- eylemler ---
        act = tk.Frame(outer, bg=BG)
        act.pack(fill="x", pady=(0, 10))

        ttk.Button(act, text="Listeyi çöz", style="Accent.TButton", command=self.resolve_list).pack(side="left")
        ttk.Button(act, text="Tümünü seç", style="Ghost.TButton", command=self.check_all).pack(side="left", padx=(6, 0))
        ttk.Button(act, text="Seçimi kaldır", style="Ghost.TButton", command=self.uncheck_all).pack(side="left", padx=(6, 0))
        ttk.Button(act, text="Temizle", style="Ghost.TButton", command=self.clear_items).pack(side="left", padx=(6, 0))

        self.stop_btn = ttk.Button(act, text="Durdur", style="Ghost.TButton", command=self.stop, state="disabled")
        self.stop_btn.pack(side="right")
        ttk.Button(act, text="Tümünü indir", style="Accent.TButton", command=self.download_all).pack(side="right", padx=(0, 6))
        ttk.Button(act, text="Seçilenleri indir", style="Ghost.TButton", command=self.download_checked).pack(side="right", padx=(0, 6))

        # --- liste kutusu ---
        wrap = tk.Frame(outer, bg=BG, highlightthickness=1, highlightbackground=LINE)
        wrap.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.inner = tk.Frame(self.canvas, bg=BG)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._wheel)

        # --- durum ---
        self.status = tk.Label(outer, text="Hazır.", bg=BG, fg=MUTED, font=("Helvetica Neue", 11))
        self.status.pack(anchor="w", pady=(8, 4))

        self.log = tk.Text(outer, height=5, bg=PANEL, fg=MUTED, relief="flat",
                           highlightthickness=1, highlightbackground=LINE,
                           font=("Menlo", 10), padx=10, pady=6, state="disabled")
        self.log.pack(fill="x")

        threading.Thread(target=self.dl_worker, daemon=True).start()
        self.pump()
        self.root.after(500, self.resolve_list)

    def style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG,
                    arrowcolor=FG, bordercolor=LINE, lightcolor=PANEL, darkcolor=PANEL)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL)])
        s.configure("Ghost.TButton", background="#242427", foreground=FG, borderwidth=0,
                    focusthickness=0, padding=(10, 6), font=("Helvetica Neue", 11))
        s.map("Ghost.TButton", background=[("active", "#303034"), ("disabled", "#1b1b1d")],
              foreground=[("disabled", "#5a5a5e")])
        s.configure("Accent.TButton", background=ACCENT, foreground="#06121f", borderwidth=0,
                    focusthickness=0, padding=(12, 6), font=("Helvetica Neue", 11, "bold"))
        s.map("Accent.TButton", background=[("active", "#6fb7ff"), ("disabled", "#26394d")],
              foreground=[("disabled", "#6b7d8d")])
        s.configure("TCheckbutton", background=BG, foreground=FG, focusthickness=0)
        s.map("TCheckbutton", background=[("active", BG)])
        for name, color in (("Blue", ACCENT), ("Green", GREEN), ("Red", RED)):
            s.configure(f"{name}.Horizontal.TProgressbar", troughcolor=LINE, bordercolor=LINE,
                        background=color, lightcolor=color, darkcolor=color, thickness=6)
        s.configure("Vertical.TScrollbar", background="#2a2a2d", troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED)

    def _wheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # --- dosya ---
    def pick_list(self):
        p = filedialog.askopenfilename(title="Liste seç",
                                       filetypes=[("Metin dosyası", "*.txt"), ("Tümü", "*.*")])
        if p:
            self.path_var.set(p)
            self.load_file()

    def load_file(self):
        p = self.path_var.get().strip()
        if not p or not os.path.isfile(p):
            messagebox.showwarning("Dosya yok", "Geçerli bir liste dosyası seç.")
            return
        try:
            with open(p, encoding="utf-8") as f:
                c = f.read()
        except Exception as e:
            messagebox.showerror("Okunamadı", str(e))
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", c)
        self.status.configure(text=f"Yüklendi: {p}")

    def save_file(self):
        p = self.path_var.get().strip()
        if not p:
            p = filedialog.asksaveasfilename(title="Kaydet", defaultextension=".txt",
                                             filetypes=[("Metin dosyası", "*.txt")])
            if not p:
                return
            self.path_var.set(p)
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end").strip() + "\n")
        except Exception as e:
            messagebox.showerror("Kaydedilemedi", str(e))
            return
        self.status.configure(text=f"Kaydedildi: {p}")

    def pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(d)

    # --- çözme ---
    def resolve_list(self):
        urls = parse_urls(self.text.get("1.0", "end"))
        if not urls:
            messagebox.showwarning("Liste boş", "Önce URL gir.")
            return
        self.status.configure(text="Video bilgileri alınıyor...")
        threading.Thread(target=self.resolver, args=(urls,), daemon=True).start()

    def resolver(self, urls):
        opts = {"extract_flat": "in_playlist", "quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            for u in urls:
                try:
                    info = ydl.extract_info(u, download=False)
                except Exception as e:
                    self.q.put(("log", f"çözülemedi: {u} -> {e}"))
                    continue
                if not info:
                    continue
                entries = info.get("entries")
                if entries:
                    for ent in entries:
                        if not ent:
                            continue
                        link = ent.get("webpage_url") or ent.get("url") or ""
                        if ent.get("id") and not link.startswith("http"):
                            link = "https://www.youtube.com/watch?v=" + ent["id"]
                        self.q.put(("add", {"url": link,
                                            "title": ent.get("title") or ent.get("id") or link,
                                            "dur": ent.get("duration")}))
                else:
                    self.q.put(("add", {"url": info.get("webpage_url") or u,
                                        "title": info.get("title") or u,
                                        "dur": info.get("duration")}))
        self.q.put(("resolved", None))

    def add_row(self, data):
        url = data["url"]
        if not url or url in self.seen:
            return
        self.seen.add(url)

        item = {"url": url, "title": data["title"], "var": tk.BooleanVar(value=True),
                "state": "idle"}

        rowf = tk.Frame(self.inner, bg=BG, pady=4)
        rowf.pack(fill="x")
        rowf.columnconfigure(1, weight=1)

        ttk.Checkbutton(rowf, variable=item["var"]).grid(row=0, column=0, rowspan=2, sticky="w")

        title = data["title"]
        if len(title) > 82:
            title = title[:79] + "..."
        tk.Label(rowf, text=title, bg=BG, fg=FG, anchor="w",
                 font=("Helvetica Neue", 11)).grid(row=0, column=1, sticky="ew", padx=(4, 8))

        bar = ttk.Progressbar(rowf, style="Blue.Horizontal.TProgressbar", maximum=100)
        bar.grid(row=1, column=1, sticky="ew", padx=(4, 8), pady=(3, 0))

        dur = fmt_dur(data.get("dur"))
        if dur:
            tk.Label(rowf, text=dur, bg=BG, fg=MUTED, width=8,
                     font=("Menlo", 10)).grid(row=0, column=2, sticky="e")

        state_lbl = tk.Label(rowf, text="", bg=BG, fg=MUTED, width=11, anchor="e",
                             font=("Helvetica Neue", 10))
        state_lbl.grid(row=1, column=2, sticky="e")

        btn = ttk.Button(rowf, text="İndir", style="Ghost.TButton", width=7,
                         command=lambda: self.download_one(item))
        btn.grid(row=0, column=3, rowspan=2, padx=(8, 0))

        tk.Frame(self.inner, bg=LINE, height=1).pack(fill="x")

        item.update({"row": rowf, "bar": bar, "state_lbl": state_lbl, "btn": btn})
        self.items.append(item)
        self.status.configure(text=f"{len(self.items)} video listelendi.")

    def check_all(self):
        for it in self.items:
            it["var"].set(True)

    def uncheck_all(self):
        for it in self.items:
            it["var"].set(False)

    def clear_items(self):
        for it in self.items:
            it["row"].destroy()
        self.items.clear()
        self.seen.clear()
        self.status.configure(text="Liste temizlendi.")

    # --- indirme ---
    def current_mode(self):
        m = self.mode_cb.get().split(" - ")[0]
        return m if m in ytdl.FORMATS else "best"

    def download_one(self, item):
        if item["state"] in ("run", "done"):
            return
        self.queue_items([item])

    def download_checked(self):
        sel = [i for i in self.items if i["var"].get() and i["state"] not in ("run", "done")]
        if not sel:
            messagebox.showwarning("Seçim yok", "İndirilecek video seçili değil.")
            return
        self.queue_items(sel)

    def download_all(self):
        sel = [i for i in self.items if i["state"] not in ("run", "done")]
        if not sel:
            messagebox.showwarning("Liste boş", "Önce listeyi çöz.")
            return
        self.queue_items(sel)

    def queue_items(self, items):
        self.stop_flag.clear()
        self.running = True
        self.stop_btn.configure(state="normal")
        self.ok.clear()
        self.fail.clear()
        mode = self.current_mode()
        outdir = self.dir_var.get().strip() or os.path.expanduser("~/Downloads")

        for it in items:
            it["state"] = "queued"
            it["bar"]["value"] = 0
            it["bar"].configure(style="Blue.Horizontal.TProgressbar")
            it["state_lbl"].configure(text="sırada", fg=MUTED)
            self.pending += 1
            self.jobs.put((it, mode, outdir))

        self.status.configure(text=f"{len(items)} video kuyruğa alındı.")

    def stop(self):
        self.stop_flag.set()
        self.status.configure(text="Durduruluyor...")

    def dl_worker(self):
        while True:
            job = self.jobs.get()
            if not isinstance(job, tuple) or len(job) != 3:
                continue
            item, mode, outdir = job

            if self.stop_flag.is_set():
                self.q.put(("finish", (item, "skip", None)))
                continue

            os.makedirs(outdir, exist_ok=True)
            self.q.put(("run", item))
            self.q.put(("log", f"-> {item['url']}"))

            def hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    done = d.get("downloaded_bytes") or 0
                    if total:
                        self.q.put(("pct", (item, done * 100 / total)))
                elif d.get("status") == "finished":
                    self.q.put(("pct", (item, 100)))

            try:
                opts = ytdl.make_opts(outdir, mode, hook)
                opts["download_archive"] = ARCHIVE
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([item["url"]])
                self.q.put(("finish", (item, "ok", None)))
            except Exception as e:
                self.q.put(("finish", (item, "err", str(e)[:160])))

    # --- pompa ---
    def log_msg(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", str(msg).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def on_run(self, item):
        item["state"] = "run"
        item["state_lbl"].configure(text="indiriliyor", fg=ACCENT)

    def on_pct(self, item, pct):
        try:
            item["bar"]["value"] = pct
        except tk.TclError:
            pass

    def on_finish(self, item, status, err):
        self.pending = max(0, self.pending - 1)

        if status == "ok":
            item["state"] = "done"
            item["bar"]["value"] = 100
            item["bar"].configure(style="Green.Horizontal.TProgressbar")
            item["state_lbl"].configure(text="✓ indi", fg=GREEN)
            item["var"].set(False)
            self.ok.append(item["title"])
            self.q.put(("log", "   tamam"))
        elif status == "skip":
            item["state"] = "skip"
            item["bar"].configure(style="Blue.Horizontal.TProgressbar")
            item["state_lbl"].configure(text="atlandı", fg=MUTED)
            self.fail.append((item["title"], "durduruldu"))
            self.q.put(("log", "   atlandı"))
        else:
            item["state"] = "err"
            item["bar"]["value"] = 100
            item["bar"].configure(style="Red.Horizontal.TProgressbar")
            item["state_lbl"].configure(text="hata", fg=RED)
            self.fail.append((item["title"], err or "bilinmeyen"))
            self.q.put(("log", f"   hata: {err}"))

        if self.pending == 0:
            self.finish_all()

    def finish_all(self):
        self.running = False
        self.stop_btn.configure(state="disabled")
        ok, fail = len(self.ok), len(self.fail)
        self.status.configure(text=f"Bitti. {ok} indirildi, {fail} indirilemedi.")

        lines = []
        if ok:
            lines.append(f"İNDİRİLENLER ({ok})")
            lines += [f"  ✓ {t}" for t in self.ok[:15]]
            if ok > 15:
                lines.append(f"  ... +{ok - 15} tane daha")
        if fail:
            lines.append("")
            lines.append(f"İNDİRİLEMEYENLER ({fail})")
            lines += [f"  ✗ {t[:70]} — {e}" for t, e in self.fail[:15]]
            if fail > 15:
                lines.append(f"  ... +{fail - 15} tane daha")

        if lines:
            messagebox.showinfo("İşlem bitti", "\n".join(lines))

    def pump(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "add":
                    self.add_row(payload)
                elif kind == "resolved":
                    self.status.configure(text=f"Çözüldü: {len(self.items)} video.")
                elif kind == "run":
                    self.on_run(payload)
                elif kind == "pct":
                    self.on_pct(*payload)
                elif kind == "finish":
                    self.on_finish(*payload)
                elif kind == "log":
                    self.log_msg(payload)
        except queue.Empty:
            pass
        self.root.after(100, self.pump)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
