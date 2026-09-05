# -*- coding: utf-8 -*-
"""
Google Fonts must not block the scripts after it.

The correct shape is TWO tags: the non-blocking media="print"/onload one that
actually loads the stylesheet, and a plain one inside <noscript> as the fallback
for readers with JavaScript off. A bare second <link rel="stylesheet"> outside
<noscript> is the bug — it blocks, and the surface goes blank whenever
fonts.googleapis.com is slow.

Note, 5 Sep 2026: the PUBLISHED deck already had the <noscript> wrapper; only the
repo copy of src/deck.html was stale and carried the bare blocking tag. The repo
has since been rebuilt from the published artifact. Check src/atlas.html against
its published version before assuming the repo copy is authoritative there either.

Run:  python build/deck_fontfix.py src/atlas.html
"""
import io, sys

HREF = ('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&'
        'family=IBM+Plex+Sans:wght@400;500;600&family=Saira+Condensed:wght@500;600;700&display=swap')
BARE = '<link rel="stylesheet" href="%s">' % HREF
WRAPPED = '<noscript>%s</noscript>' % BARE

for path in sys.argv[1:]:
    s = io.open(path, encoding="utf-8").read()
    if WRAPPED in s:
        print("%s: already correct (noscript fallback present)" % path); continue
    if s.count(BARE) != 1:
        print("%s: found %d bare tags, skipped" % (path, s.count(BARE))); continue
    io.open(path, "w", encoding="utf-8", newline="").write(s.replace(BARE, WRAPPED))
    print("%s: blocking font link wrapped in <noscript>" % path)
