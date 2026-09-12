"""
build_ice_surface — assemble the 6.25 km ice surface from the template.

Inputs
    build/ice_surface.template.html   the surface, with two substitution points
    ingest/olympus_proj.js            inlined, not fetched: an artifact cannot fetch
    data/asi/manifest.json            one record per frame, with its provenance
    data/asi/<frame>.png              the packed field

Output
    dist/ice_surface.html             self-contained, ready to publish

The PNGs go in as data URIs because a published artifact's sandbox blocks every
runtime fetch, including for images. Same data, two transports: the site build
can reference the same files by path.

Usage
    python3 build/build_ice_surface.py --north asi-n6250-20260911 --south asi-s6250-20260911
"""

import argparse
import base64
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def pick(frames, frame_id, hemisphere):
    if frame_id:
        for r in frames:
            if r["id"] == frame_id:
                return r
        raise SystemExit(f"no frame {frame_id} in the manifest")
    candidates = [r for r in frames if r["hemisphere"] == hemisphere]
    if not candidates:
        raise SystemExit(f"manifest carries no {hemisphere} frame")
    return sorted(candidates, key=lambda r: r["observed"])[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--north", help="frame id; default is the latest Arctic frame")
    ap.add_argument("--south", help="frame id; default is the latest Antarctic frame")
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "asi"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "ice_surface.html"))
    args = ap.parse_args()

    manifest = json.load(io.open(os.path.join(args.data, "manifest.json"), encoding="utf-8"))
    frames = manifest["frames"]

    chosen = {
        "n": pick(frames, args.north, "Arctic"),
        "s": pick(frames, args.south, "Antarctic"),
    }

    payload = {}
    for key, rec in chosen.items():
        png = os.path.join(args.data, rec["encoding"]["file"])
        slim = {k: rec[k] for k in (
            "id", "hemisphere", "observed", "parameter", "units", "mode",
            "instrument", "algorithm", "producer", "resolution_m", "epsg",
            "width", "height", "statistics", "encoding", "citation")}
        slim["source"] = {k: rec["source"][k] for k in
                          ("url", "retrieved_utc", "http_last_modified", "sha256", "bytes")}
        slim["png"] = data_uri(png)
        payload[key] = slim

    tpl = io.open(os.path.join(ROOT, "build", "ice_surface.template.html"),
                  encoding="utf-8").read()
    proj = io.open(os.path.join(ROOT, "ingest", "olympus_proj.js"), encoding="utf-8").read()

    if "__PROJ_JS__" not in tpl or "__FRAMES_JSON__" not in tpl:
        raise SystemExit("template is missing a substitution point")

    html = tpl.replace("__PROJ_JS__", proj)
    html = html.replace("__FRAMES_JSON__",
                        json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(args.out)
    print(f"{args.out}  {size/1024/1024:.2f} MB")
    for key, rec in chosen.items():
        print(f"  {key}: {rec['id']}  {rec['width']}x{rec['height']}  EPSG:{rec['epsg']}  "
              f"extent {rec['statistics']['extent_km2']/1e6:.2f} M km2")
    if size > 16 * 1024 * 1024:
        print("WARNING: over the 16 MB artifact ceiling", file=sys.stderr)


if __name__ == "__main__":
    main()
