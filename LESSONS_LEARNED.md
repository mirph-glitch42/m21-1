# Lessons Learned

Authoritative record of lessons learned during the development of this system:
the situation, the pitfall, and the correct solution for each lesson.
Managed by the `learned-lesson-tracker` skill — do not edit the index block or
the entry markers by hand; use `scripts/manage_lessons.py` (init / add / sync /
check / next-id). The index below is machine-readable (TSV between
`LLT:INDEX:BEGIN`/`LLT:INDEX:END` markers) and lists every entry with its
line range.

<!-- LLT:INDEX:BEGIN -->
id	title	category	severity	status	recorded	start_line	end_line
LLT_INDEX_BLOCK	—	—	—	—	—	11	16
LLT-0001	SonarCloud S8707 only credits its documented compliant sanitizer pattern	security	high	active	2026-10-15	18	31
LLT-0002	In-cell lists: find_all('li') double-renders nested items; '; '-join flattens the list — emit real HTML <ul>/<ol>/<li>	debugging	high	active	2026-10-17	32	45
<!-- LLT:INDEX:END -->

<!-- LLT:ENTRY:LLT-0001 -->
## LLT-0001 — SonarCloud S8707 only credits its documented compliant sanitizer pattern

- **Recorded:** 2026-10-15
- **Category:** security
- **Severity:** high
- **Status:** active
- **Context:** B22 - SonarCloud security gate for mirph-glitch42/m21-1 failed with four pythonsecurity:S8707 flags (Path Traversal via LLM-supplied CLI arguments) in scripts/build_index.py and src/m21_crawl/cli.py; three fix commits (commonpath helper, helper mirror, inlined-into-sink eaeb0af) were all re-flagged on re-analysis.
- **Pitfall:** Assuming any semantically equivalent containment check is credited: os.path.commonpath([root, target]) != root is NOT credited in either helper or inline form; and treating files without S8707 issues (check_index_registry.py, gen_b20_nested_table.py) as evidence the helper shape is credited - their rel arguments are constants, so no taint source exists and they say nothing about sanitizer credit.
- **Solution:** Mirror the rule's own Compliant solution exactly: a helper that computes resolved = os.path.realpath(path) and base_dir = os.path.realpath(<getcwd-derived base>), raises when resolved != base_dir and not resolved.startswith(base_dir + os.sep) (explicit trailing separator), and returns resolved; sinks call the helper. Never add # nosem without explicit user approval.
- **Supersedes:** —
- **Prevention:** When Sonar re-flags after a fix, fetch the full rule description (api/rules/show) and replicate its Compliant solution structure verbatim instead of guessing which sanitizer shape the engine credits.
- **References:** —

<!-- LLT:ENTRY:LLT-0002 -->
## LLT-0002 — In-cell lists: find_all('li') double-renders nested items; '; '-join flattens the list — emit real HTML <ul>/<ol>/<li>

- **Recorded:** 2026-10-17
- **Category:** debugging
- **Severity:** high
- **Status:** active
- **Context:** B25/B26 (M21-1 manual): lists inside GFM table cells — nested <ul> inside a <li> duplicated every sub-item (emitted in place AND again as a separate block); flat <ul>/<ol> were folded into one inline string joined by '; ', losing bullets and <ol> numbering. Goal-1 ORGANIZATION violation, user-reported 2026-10-16; root function _render_list_inline in src/m21_crawl/mdconv.py.
- **Pitfall:** BeautifulSoup find_all('li') on a list element iterates ALL descendant li, so any <ul> nested inside a <li> is emitted twice (once within the parent's flattened text, once as its own block); and joining li texts with '; ' serializes list structure into prose — bullets lost, <ol> numbering lost, organization changed. Both symptoms share the one root function, so a partial fix (dedupe or un-flatten) leaves the other.
- **Solution:** Emit a real HTML list inside the cell: <ul>/<ol> containing only the list element's DIRECT li children (iterate direct children, not find_all('li')); nested lists recurse as real nested <ul>/<ol>; inline content preserved verbatim. Renderers (GitHub, VMD) process HTML lists inside GFM cells — verified via the render-test loop (render-test/b25b26-html-lists.md, user-approved 2026-10-17) and TESTS cases 19, 82-85. Census on regenerated manual: duplicated-sub-item rows 613->0; flattened '; '-joined rows 1,400->4 (legitimate prose); real in-cell lists 0->3,693; table rows unchanged 18,292.
- **Supersedes:** —
- **Prevention:** When rendering a list, iterate the list element's direct children, never find_all('li') (descends into nested lists); and never serialize list structure into '; '-joined prose — a list is structure, so keep it a list.
- **References:** backlog.md B25/B26; algorithms/html-to-markdown-section-extraction.md 0.17.0; render-test/b25b26-html-lists.md; src/m21_crawl/mdconv.py _render_list_inline
