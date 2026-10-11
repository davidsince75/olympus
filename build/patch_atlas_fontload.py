#!/usr/bin/env python3
"""patch_atlas_fontload.py — let the Station Network's web fonts switch on.

The font stylesheet is loaded non-blocking (media="print", switched to "all"
once it loads). On this surface the handler had been written with escaped
quotes, onload="this.media=\\'all\\'", which in an HTML attribute is a
backslash followed by a quote: a JavaScript syntax error. The handler threw
("Invalid or unexpected token") the moment the stylesheet arrived, the switch
never happened, and the page has rendered in fallback system fonts instead of
IBM Plex and Saira. The deck and The Named Ice carry the correct attribute.

Found on 11 Oct 2026, when the live site was first opened with Google Fonts
reachable; every local check had blocked the font request.

usage: python build/patch_atlas_fontload.py IN OUT [--dry-run]
"""
import argparse, hashlib, sys

OLD = '''onload="this.media=\\'all\\'"'''
NEW = '''onload="this.media='all'"'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s = open(a.src, encoding="utf-8", newline="").read()
    n = s.count(OLD)
    print(f"  html:font-onload   matches={n}")
    if n != 1: sys.exit("ABORT: anchor not matched exactly once")
    if a.dry_run: print("dry run: anchor unique, nothing written"); return
    s = s.replace(OLD, NEW, 1)
    open(a.out, "w", encoding="utf-8", newline="").write(s)
    b = s.encode("utf-8")
    print(f"wrote {a.out}  {len(b):,} bytes  sha256={hashlib.sha256(b).hexdigest()[:16]}")

if __name__ == "__main__":
    main()
