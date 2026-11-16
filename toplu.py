#!/usr/bin/env python3
"""toplu.py - bir metin dosyasindaki tum URL'leri indirir.
Kullanim: python toplu.py liste.txt [-f 1080] [-o ~/Downloads]
Dosya formati: her satira bir URL, # ile baslayan satirlar yorum.
Ayni video ikinci kez indirilmez (arsiv dosyasi tutulur).
"""

import argparse
import os
import sys

import ytdl

ARCHIVE = os.path.expanduser("~/.ytdl_archive.txt")


def read_list(path):
    with open(path, encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


def main():
    p = argparse.ArgumentParser(description="Listeden toplu indirme")
    p.add_argument("liste", help="URL listesi iceren .txt dosyasi")
    p.add_argument("-o", "--out", default=os.path.expanduser("~/Downloads"))
    p.add_argument("-f", "--format", default="best", choices=ytdl.FORMATS.keys())
    a = p.parse_args()

    if not os.path.isfile(a.liste):
        sys.exit(f"Dosya yok: {a.liste}")

    urls = read_list(a.liste)
    if not urls:
        sys.exit("Liste bos.")

    print(f"{len(urls)} URL bulundu. Cikti: {a.out}\n")

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")

        def hook(d, _i=i, _n=len(urls)):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes") or 0
                if total:
                    pct = done * 100 / total
                    sys.stdout.write(f"\r  %{pct:5.1f}  {d.get('_speed_str','').strip()}   ")
                    sys.stdout.flush()
            elif d.get("status") == "finished":
                print("\r  tamam, isleniyor...            ")

        opts = ytdl.make_opts(a.out, a.format, hook)
        opts["download_archive"] = ARCHIVE
        try:
            with ytdl.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except KeyboardInterrupt:
            print("\nIptal edildi.")
            sys.exit(0)
        except Exception as e:
            print(f"  atlandi: {e}")
        print()

    print("Liste bitti.")


if __name__ == "__main__":
    main()
