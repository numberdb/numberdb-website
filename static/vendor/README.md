# Vendored third-party assets

Third-party code and fonts, checked in and served from this site rather than
from a CDN. Not because the CDNs are unreliable, but because a browser fetching
a file from another host tells that host who is reading which page of NumberDB,
before the reader has clicked anything and without anyone asking them. Four
such embeds were live at once; `numberdb_app/test_no_third_party_assets.py`
keeps them from coming back.

Recorded here because "where did this file come from" is a question that is
very hard to answer later, and these are files nobody wrote.

| What | Version | Where it came from | Licence |
| --- | --- | --- | --- |
| MathJax (`mathjax/tex-svg.js`) | 3 | `https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js` | Apache-2.0 |
| highlight.js (`highlight/`) | 10.5.0 | `https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@10.5.0/build/` | BSD-3-Clause |
| Source Sans Pro (`../fonts/sourcesanspro-*.woff2`) | as served 2026-08-10 | Google Fonts css2 | SIL OFL 1.1 |
| Rye (`../fonts/rye-*.woff2`) | as served 2026-08-10 | Google Fonts css2 | SIL OFL 1.1 |

The `tex-svg` build is the single-file one: it carries its own font data as SVG
paths, so it fetches nothing further at runtime. That is why it is 2 MB, and
why it is the right build to vendor.

`../css/fonts.css` is Google's own css2 stylesheet with every `url()` rewritten
to point at `../fonts/`. The `unicode-range` declarations are untouched, so a
browser still downloads only the subsets it needs -- 23 files exist, a European
visitor fetches two or three.

## Replacing one

Download the new file, drop it in, and update the version in the table above.
Nothing is minified or built here, and nothing imports from anywhere else, so
there is no build step to re-run and no lockfile to keep in step.

To refresh the fonts, fetch the css2 URL **with a browser's User-Agent** --
Google serves woff2 only to browsers it recognises, and a bare `curl` gets the
much larger and older ttf -- then rewrite each `url()` to `../fonts/NAME` and
save the files under those names.
