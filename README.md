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

<!-- TODO -->

## Query bytes

All on the 2026-10-01 crawl, run on 2026-11-03:

| Query | Bytes processed |
|---|---|
| queries/hits.sql | 113,818,805,526 (dry-run upper bound) |
| queries/totals.sql | 470,973,689 (dry-run upper bound) |
