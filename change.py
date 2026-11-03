# The change under test. compare.py, recheck.py, and analyze.py import this; the rest is generic.
# Visits A and A2 use the "before" setup, B the "after" setup. Leave unused hooks as they are.
#
# Change: the HTML parser no longer inserts </select> when it sees <input> while a <select> is in
# scope, so <input> stays inside <select> (directly, inside <option>/<optgroup>, or inside other
# elements). Implemented in a patched Chromium build behind the InputInSelect runtime flag.

# Browser launch arguments, e.g. ['--disable-blink-features=Foo'] or ['--disable-features=Foo'].
BEFORE_ARGS = []
AFTER_ARGS = ['--enable-blink-features=InputInSelect']

# Unpacked extension directory to load in that setup, e.g. a polyfill extension in AFTER with the
# native feature off in AFTER_ARGS. Each visit then gets a fresh profile.
BEFORE_EXTENSION = None
AFTER_EXTENSION = None

# Emulation, when no switch or build implements the change: a script injected before page scripts
# run (parse-time and API changes), and/or an async function expression run in B after load (DOM
# rewrites; compare.py waits again before measuring).
AFTER_INIT_JS = None
AFTER_LOAD_JS = None

# Injected into every visit before page scripts run, e.g. to record call stacks of an API.
# Records how many <input>s are inside a <select> at DOMContentLoaded, before most re-rendering.
INIT_JS = """
document.addEventListener('DOMContentLoaded', () => {
  window.__iisDCL = {
    inputsInSelect: document.querySelectorAll('select input').length,
    selects: document.querySelectorAll('select').length,
    inputs: document.querySelectorAll('input').length,
  };
}, {once: true});
"""

# Function expression returning change-specific measurements (element boxes, stacks recorded by
# INIT_JS, etc.); stored as 'extra' for the page and each frame.
EXTRA_MEASURE_JS = """
() => {
  const inSel = [...document.querySelectorAll('select input')];
  return {
    dcl: window.__iisDCL || null,
    inputsInSelect: inSel.length,
    inputsInSelectTypes: inSel.slice(0, 10).map(i => (i.getAttribute('type') || 'text').toLowerCase()),
    selects: document.querySelectorAll('select').length,
    inputs: document.querySelectorAll('input').length,
    visibleInputs: [...document.querySelectorAll('input')].filter(i => i.getClientRects().length && i.type !== 'hidden').length,
    selectOptions: [...document.querySelectorAll('select')].reduce((n, s) => n + s.options.length, 0),
    strayOptions: [...document.querySelectorAll('option')].filter(o => !o.closest('select, datalist')).length,
  };
}
"""

# Regex for console messages a setup logs by design (a flag's deprecation notice, a polyfill's
# progress logs). analyze.py sends pages with other errors or warnings only B logs to review.
IGNORE_MESSAGES = r'An <input> tag was parsed within an open <select> tag'

# Checked on sanity/<SANITY_PAGE> before the run: an expression that is true only when the change
# is in effect. compare.py stops if A is true or B is false.
SANITY_PAGE = 'index.html'
SANITY_JS = """(() => {
  const ids = ['a1', 'a2', 'b1', 'c1'];
  const inside = ids.map(id => !!document.getElementById(id).closest('select'));
  if (inside.every(x => x)) return true;
  if (inside.every(x => !x)) return false;
  throw new Error('mixed: ' + inside);
})()"""


def classify(r):
    """Change-specific auto-rating for a page analyze.py couldn't rate: (rating, reason) or None."""
    # The change only ever leaves an <input> inside a <select> that the old parser would have closed.
    # If B has no <input> inside a <select> at DOMContentLoaded or after load, in any frame, the parse
    # matched A's, so the page no longer hits the change (it changed since the crawl, or the hit was
    # in content the live load didn't get).
    def triggered(v):
        docs = [v.get('extra') or {}] + [f.get('extra') or {} for f in v.get('frames', [])]
        return any(d.get('inputsInSelect') or (d.get('dcl') or {}).get('inputsInSelect') for d in docs)
    if not triggered(r['B']):
        return 'no visible change', 'change not triggered in B (no <input> inside <select>)'
    return None
