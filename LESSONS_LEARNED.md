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
LLT_INDEX_BLOCK	—	—	—	—	—	11	15
LLT-0001	SonarCloud S8707 only credits its documented compliant sanitizer pattern	security	high	active	2026-10-15	17	30
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
