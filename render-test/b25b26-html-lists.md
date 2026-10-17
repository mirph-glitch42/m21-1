# B25/B26 render test — lists in a cell, driven by real `<ul>`/`<ol>` HTML

This test feeds actual list markup through the production
``_render_list_inline`` (BEFORE) and the proposed fix (AFTER). The BEFORE
column is the **real current output** — the symptoms are reproduced, not
asserted.

Symptoms under test: **B26** (a flat list is flattened to `; `-joined text;
`<ol>` numbering is lost) and **B25** (nested-list children are emitted
twice).

**Preferred method (user):** embed the list as HTML `<ul>`/`<ol>`/`<li>` in
the cell. It renders as a real list on every renderer (VMD, GitHub, ...),
preserves the list organization (no text/organization change), and needs no
`<br>`/`&nbsp;` shims. The AFTER cell below shows the list exactly as it
will render in the manual.

## Case 1 — flat `<ul>`

Input (HTML):

```html
<ul><li>cord</li><li>string</li><li>twine</li><li>masking tape, or</li><li>cellophane tape</li></ul>
```

| Variant | Rendered in a GFM table cell |
| --- | --- |
| **BEFORE** — current `_render_list_inline` | cord; string; twine; masking tape, or; cellophane tape |
| **AFTER** — proposed (embedded HTML list) | <ul><li>cord</li><li>string</li><li>twine</li><li>masking tape, or</li><li>cellophane tape</li></ul> |


## Case 2 — flat `<ol>` (numbering)

Input (HTML):

```html
<ol><li>Open the template</li><li>Select the representative</li><li>Verify the address</li></ol>
```

| Variant | Rendered in a GFM table cell |
| --- | --- |
| **BEFORE** — current `_render_list_inline` | Open the template; Select the representative; Verify the address |
| **AFTER** — proposed (embedded HTML list) | <ol><li>Open the template</li><li>Select the representative</li><li>Verify the address</li></ol> |


## Case 3 — nested `<ul>`

Input (HTML):

```html
<ul><li>such as<ul><li>eating</li><li>dressing</li><li>grooming, and</li><li>carrying out personal hygiene</li></ul></li></ul>
```

| Variant | Rendered in a GFM table cell |
| --- | --- |
| **BEFORE** — current `_render_list_inline` | such aseating; dressing; grooming, and; carrying out personal hygiene; eating; dressing; grooming, and; carrying out personal hygiene |
| **AFTER** — proposed (embedded HTML list) | <ul><li>such as<ul><li>eating</li><li>dressing</li><li>grooming, and</li><li>carrying out personal hygiene</li></ul></li></ul> |


## Case 4 — nested `<ol>` (numbering)

Input (HTML):

```html
<ol><li>first step<ol><li>sub a</li><li>sub b</li></ol></li></ol>
```

| Variant | Rendered in a GFM table cell |
| --- | --- |
| **BEFORE** — current `_render_list_inline` | first stepsub a; sub b; sub a; sub b |
| **AFTER** — proposed (embedded HTML list) | <ol><li>first step<ol><li>sub a</li><li>sub b</li></ol></li></ol> |


## Case 5 — mixed `<ul>` with a nested `<ol>`

Input (HTML):

```html
<ul><li>self-care, such as<ol><li>eating</li><li>dressing</li><li>grooming</li></ol></li></ul>
```

| Variant | Rendered in a GFM table cell |
| --- | --- |
| **BEFORE** — current `_render_list_inline` | self-care, such aseating; dressing; grooming; eating; dressing; grooming |
| **AFTER** — proposed (embedded HTML list) | <ul><li>self-care, such as<ol><li>eating</li><li>dressing</li><li>grooming</li></ol></li></ul> |


---

**Implementation:** `_render_list_inline` is rewritten to emit real HTML
`<ul>`/`<ol>`/`<li>` (iterate *direct* `<li>` only; keep each `<li>`'s
inline content; recurse into nested lists). That single change removes
B25 (duplication) and B26 (flattening / lost numbering) while preserving
the list's organization — matching the standing no-text / no-organization
change goal.

