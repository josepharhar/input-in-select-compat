# Compat impact of allowing `<input>` inside `<select>` in the HTML parser

Proposed change: when the HTML parser sees an `<input>` start tag while a `<select>` is in scope,
it no longer inserts a `</select>` end tag first. The `<input>` stays inside the `<select>`, whether
its parent is the `<select>` itself, an `<option>`/`<optgroup>`, or another element (e.g.
`<select><div><input>`). Content after the `<input>` up to the real `</select>` also stays in the
`<select>`, where the old parser put it after the closed select.

## Scope (agreed at kickoff)

- Crawl: HTTP Archive `httparchive.crawl.pages`, 2026-10-01, desktop and mobile, root pages only.
- Pages: every root page whose `features` include Blink use counter `InputParsedParentSelect` (5546)
  or `InputParsedAncestorSelect` (5547). There are few hits (1,014 page/client pairs), so every hit is
  loaded rather than a sample.
- Setups: one patched Chromium build (159.0.8140.0, `origin/main` of 2026-11-02 plus the patch below),
  before = default, after = `--enable-blink-features=InputInSelect`.
- Budget: $5 of BigQuery for the whole run.

## Summary

Not web compatible. Of the 1,014 root page loads (595 sites) in the 2026-10-01 crawl that hit
`InputParsedParentSelect` or `InputParsedAncestorSelect`, the change still took effect on 541 when
loaded live, and 205 of those (132 parent, 73 ancestor) looked different beyond page noise; 166
lost at least one visible `<input>` into a `<select>`, where it doesn't render. Every one of the six
largest differences reviewed by eye is broken: forms, search boxes and buttons disappear, and on
some pages the rest of the page is swallowed by the `<select>`. Both counters' cases break pages.

## 1. HTTP Archive

Counters (`third_party/blink/renderer/core/html/parser/html_tree_builder.cc`, `<input>` start tag in
body, when a `<select>` is in scope):

- `InputParsedParentSelect` (5546): the current node is the `<select>`.
- `InputParsedAncestorSelect` (5547): the current node is neither the `<select>` nor an
  `<option>`/`<optgroup>` (e.g. `<select><div><input>`).
- Not counted by either: `<input>` directly inside `<option>`/`<optgroup>` (counted by
  `InputParsedParentOptionOrOptgroup`, 5580). Pages hitting only that are not in this study.

Queries: `queries/hits.sql` -> `queries/hits.csv` (with `queries/hits-strata.csv` adding a `counter`
column: parent, ancestor, or both); `queries/totals.sql` -> `queries/totals.csv`.

| | desktop | mobile |
|---|---|---|
| Root pages crawled | 11,650,352 | 15,366,242 |
| `InputParsedParentSelect` only | 409 | 472 |
| `InputParsedAncestorSelect` only | 61 | 70 |
| Both | 2 | 0 |

595 distinct pages. Chrome field rates (chromestatus, monthly mean of daily % of page loads, Oct 2026):
5546 about 0.0072%, 5547 about 0.0010%.

## 2. Live comparison

Every hit in `queries/hits-strata.csv` (`sample.jsonl`, all 1,014 page/client pairs, strata
`<counter>-<client>`) was loaded live on 2026-11-03 with `compare.py` in Chromium 159.0.8140.0 built
from `origin/main` (2026-11-02) plus `chromium.patch`: A and A2 with default settings, B with
`--enable-blink-features=InputInSelect`; crawl-like viewports (desktop 1366x768; mobile 360x640,
DPR 3, mobile UA), `load` plus 3 s. The sanity check (`sanity/index.html`) confirmed that all four
`<input>`s (direct child before and after an option, inside an option, inside a div) are outside
the `<select>` in A and inside it in B. `change.py` records, at DOMContentLoaded and after load, how
many `<input>`s are inside a `<select>`, plus visible input counts. Output: `out/results.jsonl`
(scrubbed at capture).

Ratings (`analyze.py`, `out/auto.csv`, `out/review.csv`):

- "Not triggered": B had no `<input>` inside a `<select>` in any frame, so B parsed like A (the
  site changed since the crawl, or served different markup). Auto-rated no visible change.
- "Within noise": triggered, but A vs B differs no more than A vs A2. Auto-rated no visible change.
- "Differs": triggered and A vs B differs more than A vs A2 (text or pixels). Needs review.
- "Lost visible input": B has fewer rendered non-hidden `<input>`s than both A and A2.

| Counter | Loads | Load error | Not triggered | Triggered | Within noise | Differs | Lost visible input |
|---|---|---|---|---|---|---|---|
| `InputParsedParentSelect` | 881 | 93 | 352 | 436 | 304 | 132 | 110 |
| `InputParsedAncestorSelect` | 131 | 16 | 10 | 105 | 32 | 73 | 56 |
| Both | 2 | 1 | 1 | 0 | | | |

(Counted from `out/results.jsonl` with the rules above; `analyze.py` additionally sends pages with new
console errors only in B to review, which makes 238 pages to review.)

The run was stopped at the screening stage, as agreed, because the first pages looked at already
rule the change out: not all 238 pages were rated. The six pages below were reviewed by eye and are
all broken (`out/review.csv`, review images left A = before, right B = after):

- igarz.com (desktop, parent): the game's start panel loses its name/skin/team fields, Play button
  and option checkboxes. [out/review/367.png](out/review/367.png)
- spikedcandy.com (desktop, parent): the whole page body disappears; only the footer line is left.
  [out/review/371.png](out/review/371.png)
- rarepalmseeds.com (desktop, parent): top search and navigation disappear; a country select's
  options spill out as loose text over the page. [out/review/171.png](out/review/171.png)
- piese-drujbe.ro (desktop, parent): search box and model/product dropdowns disappear; option text
  spills down the page. [out/review/166.png](out/review/166.png)
- mein-schiffcruises.de (mobile, ancestor): the search form loses its GO button and everything below
  the form disappears. [out/review/129.png](out/review/129.png)
- jjworldleague.com (mobile, ancestor): the hero and the upcoming tournaments list disappear.
  [out/review/102.png](out/review/102.png) (one tournament name redacted)

43 pages are listed in `out/nsfw.csv`; none of the examples above.

## Not covered

- Pages hitting only `InputParsedParentOptionOrOptgroup` (5580), which the change also affects.
- Non-visual effects (form submission, scripts reading the moved inputs), interaction, logged-in
  pages, pages the crawl doesn't visit.
- Narrower variants (e.g. keeping `<input>` in `<select>` only before any `<option>`, the case
  `InputParsedParentSelectNoOptions` counts) were not measured. The ancestor-case breakage
  (mein-schiffcruises.de, jjworldleague.com) also happens under the original `InputInSelect` flag
  behavior, which kept ancestor-case inputs inside the select.

## Query bytes

All on the 2026-10-01 crawl, run on 2026-11-03:

| Query | Bytes processed |
|---|---|
| queries/hits.sql | 113,818,805,526 (dry-run upper bound) |
| queries/totals.sql | 470,973,689 (dry-run upper bound) |

## Reproduce

```sh
bq query --use_legacy_sql=false --format=csv --max_rows=1000000 < queries/hits.sql > queries/hits.csv
# add the counter column (parent/ancestor/both) -> queries/hits-strata.csv
python3 sample.py queries/hits-strata.csv sample.jsonl iis2026 100000 counter client
git -C <chromium>/src apply chromium.patch && autoninja -C out/Release chrome
python3 -m venv .venv && .venv/bin/pip install playwright pillow nudenet
.venv/bin/python compare.py <chromium>/src/out/Release/chrome sample.jsonl out --concurrency 8
.venv/bin/python nsfw_check.py out
.venv/bin/python analyze.py out
```

Live pages change, so a rerun won't match exactly. Screenshots (`out/shots/`) aren't committed.
