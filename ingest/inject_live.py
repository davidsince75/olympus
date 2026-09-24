#!/usr/bin/env python3
"""
Olympus — put a freshly built living layer into a surface.

Replaces the single line `const LIVE = {...};` in a surface with the payload
written by `ingest/build_events.py`. Exactly one such line must exist, the old
and new payloads must carry the same top-level blocks, and the new one must
parse, or nothing is written.

  python ingest/inject_live.py data/events/live.json dist/deck.html dist/atlas.html [--dry]
"""
import json
import sys

HEAD = "const LIVE = "


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if len(args) < 2:
        raise SystemExit(__doc__)
    new_txt = open(args[0], encoding="utf-8").read().strip()
    new = json.loads(new_txt)
    for path in args[1:]:
        s = open(path, encoding="utf-8", newline="").read()
        n = s.count("\n" + HEAD)
        if n != 1:
            raise SystemExit(f"ABORT {path}: '{HEAD}' at line start matched {n} times, need 1")
        i = s.find("\n" + HEAD) + 1
        j = s.find("\n", i)
        old = json.loads(s[i + len(HEAD):j].rstrip().rstrip(";"))
        missing = set(old) - set(new)
        if missing:
            raise SystemExit(f"ABORT {path}: new payload lacks blocks {sorted(missing)}")
        out = s[:i] + HEAD + new_txt + ";" + s[j:]
        print(f"  ok  {path}: LIVE built {old['meta']['built']} -> {new['meta']['built']}"
              f"  ({(j-i)/1e3:.0f} KB -> {(len(new_txt)+len(HEAD)+1)/1e3:.0f} KB)")
        if not dry:
            open(path, "w", encoding="utf-8", newline="").write(out)
    if dry:
        print("dry run — nothing written")


if __name__ == "__main__":
    main()
