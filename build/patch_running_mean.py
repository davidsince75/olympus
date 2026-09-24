#!/usr/bin/env python3
"""
Olympus — the timeline's running mean is twelve months or nothing.

Found while building the Deck log (24 Sep 2026). The bright line on the
timeline is described as a 12-month running mean "which strips the season out
and leaves the trend". It averaged frames i-6 .. i+5, clipped at the ends of the
record, and counted frames rather than months. So:

  - the last five points and the first six were means of 7 to 11 months, and a
    part-year mean still carries the season. The newest point, August 2026, was
    the mean of February to August: in the Antarctic that is the growth season
    alone, drawn as if it were a year.
  - across the gaps (April-June 1986, December 1987) a 12-frame window spans 13
    to 15 calendar months.

Now a point is drawn only where frames i-6 .. i+5 exist and are twelve
consecutive calendar months. The line stops six months short of each end and
breaks at the gaps, which is what the data supports. The thin monthly line is
unchanged and still runs to the newest month.

  python build/patch_running_mean.py [--dry]     # patches dist/deck.html
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

OLD = """    const rm=[];
    for(let i=0;i<m;i++){
      let a=Math.max(0,i-6), b=Math.min(m-1,i+5), t=0;
      for(let q=a;q<=b;q++) t+=E[q];
      rm.push(t/(b-a+1));
    }
    g.strokeStyle=TONE[hh][1]; g.lineWidth=1.9; g.beginPath();
    rm.forEach((v,i)=>{ (i && O[i]===O[i-1]+1) ? g.lineTo(Xh(i),Y(v)) : g.moveTo(Xh(i),Y(v)); });"""

NEW = """    // twelve consecutive calendar months or no point at all: a window clipped
    // at the ends of the record, or one spanning a gap, still carries the season
    const rm=[];
    for(let i=0;i<m;i++){
      const a=i-6, b=i+5;
      if(a<0 || b>m-1 || O[b]-O[a]!==11){ rm.push(null); continue; }
      let t=0; for(let q=a;q<=b;q++) t+=E[q];
      rm.push(t/12);
    }
    g.strokeStyle=TONE[hh][1]; g.lineWidth=1.9; g.beginPath();
    rm.forEach((v,i)=>{ if(v===null) return; (i && rm[i-1]!==null && O[i]===O[i-1]+1) ? g.lineTo(Xh(i),Y(v)) : g.moveTo(Xh(i),Y(v)); });"""

EX_OLD = ' b:"570 monthly composites. The thin line is every month; the bright line is the 12-month running mean, which strips the season out and leaves the trend.'
EX_NEW = (' b:"570 monthly composites. The thin line is every month; the bright line is the 12-month running mean, which strips the season out '
          'and leaves the trend. It is drawn only where twelve consecutive months exist, so it stops six months short of each end of the record '
          'and breaks at the gaps: a shorter window would still carry the season.')

EDITS = [("running mean: whole years only", OLD, NEW, 1),
         ("timeline explainer says where the mean stops", EX_OLD, EX_NEW, 1)]


def main():
    dry = "--dry" in sys.argv
    path = os.path.join(ROOT, "dist", "deck.html")
    src = open(path, encoding="utf-8", newline="").read()
    out = src
    for name, old, new, want in EDITS:
        n = out.count(old)
        if n != want:
            raise SystemExit(f"ABORT — '{name}': anchor matched {n} times, need {want}")
        out = out.replace(old, new, want)
        print(f"  ok  {name}")
    if "Math.max(0,i-6), b=Math.min(m-1,i+5)" in out:
        raise SystemExit("ABORT — guard: the clipped window is still there")
    if dry:
        print("dry run — nothing written")
        return
    open(path, "w", encoding="utf-8", newline="").write(out)
    print("written dist/deck.html")


if __name__ == "__main__":
    main()
