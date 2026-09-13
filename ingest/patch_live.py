#!/usr/bin/env python3
"""
Olympus — stop rebuilding the living layer on every frame.

The aurora, the SAR footprints and the ice drift are single observations that do
not move. They were being redrawn from scratch 60 times a second, at ~12,000
separate path fills and strokes per frame, which is where the polar discs lost
their frame rate. This replaces drawDeckLive with a cached, batched version.

Exact-string anchor, must match exactly once.

  python ingest/patch_live.py dist/deck.html [--dry]
"""
import sys, os, shutil

here = os.path.dirname(__file__)
OLD = open(os.path.join(here, "..", "build", "old_drawDeckLive.txt"), encoding="utf-8").read()
NEW = open(os.path.join(here, "..", "build", "live_cache.js"), encoding="utf-8").read()


def main():
    deck = sys.argv[1]
    dry = "--dry" in sys.argv
    src = open(deck, encoding="utf-8", newline="").read()
    n = src.count(OLD)
    if n != 1:
        raise SystemExit(f"ABORT — drawDeckLive anchor matched {n} times, need 1")
    out = src.replace(OLD, NEW.rstrip() + "\n", 1)
    print("  ok  drawDeckLive -> cached + batched")
    if dry:
        print(f"dry run — {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB, nothing written")
        return
    shutil.copyfile(deck, deck + ".prelive")
    open(deck, "w", encoding="utf-8", newline="").write(out)
    print(f"written {deck}  {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB")


if __name__ == "__main__":
    main()
