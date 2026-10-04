# M21-1 Manual Crawler

Builds the **complete, in-order** *M21-1 Adjudication Procedures Manual* from the
VA Knowva eBenefits self-service portal and renders it as a single Markdown file.

- **Source:** <https://www.knowva.ebenefits.va.gov> (Knowva portal `554400000001018`,
  root topic `554400000004049`)
- **Output:** [`output/M21-1-Adjudication-Procedures-Manual.md`](output/M21-1-Adjudication-Procedures-Manual.md)
- **Content license:** the manual is a work of the U.S. Government (public domain);
  this repository only adds original crawler code and formatting.

## How it works

```
          +----------------+   anonymous session    +---------------------------------+
          |  CLI (cli.py)  | ----------------------> | Knowva eGain API (ws/v11, ws/v15) |
          +----------------+   topic tree / articles |                                 |
                |                                             |                         |
                v                                             v                         |
        +----------------+   flatten, dedupe,  +----------------+   HTML -> Markdown   |
        |  tree.py       |   preserve manual   |  mdconv.py     |                      |
        | (crawl state)  |   order             +----------------+                      |
        +----------------+                                                   |         |
                |                                                           v         |
                v                                                   +----------------+
        +----------------+                                            | assemble.py  |
        | client.py      |  retries, session refresh, timeouts       +-------+------+
        +----------------+                                                       |
                                                                                 v
                                                        output/M21-1-Adjudication-Procedures-Manual.md
```

1. `session.py` — POSTs an anonymous login and keeps the `X-egain-session` token.
2. `tree.py` — crawls the topic hierarchy level-by-level (Manual → Part → Subpart →
   Chapter), deduplicating by topic id, preserving portal (manual) order.
3. `articles.py` — lists each topic's articles (in portal order); skips articles
   whose names are marked **Historical** or **Rescinded** (never fetched) and
   fetches content for the rest.
4. `mdconv.py` — converts each article's rich HTML to clean GitHub-Flavored Markdown.
5. `assemble.py` — stitches everything into one ordered document and verifies
   completeness with two gates: the listed article count matches the portal's
   own root total (truncation backstop), and the assembled count matches
   listed − excluded (see `algorithms/historical-rescinded-exclusion.md`).

## Setup

```bash
make setup        # venv + pinned deps + git hooks
make gate         # format-check -> lint -> doc-index -> tests -> secrets
```

## Run the crawler

```bash
make crawl        # writes output/M21-1-Adjudication-Procedures-Manual.md
```

No credentials are required: the portal is publicly readable and the crawler uses
the same anonymous session flow as a browser.

## Gates (DevSecOps)

- **Local git hooks** (`hooks/`, wired via `core.hooksPath`):
  - `pre-commit` — ruff format check → ruff lint → gitleaks (staged) → fast tests
  - `commit-msg` — Conventional Commits
  - `pre-push` — full suite → algorithm-doc index freshness → gitleaks (full history)
- **CI** (`.github/workflows/ci.yml`) — same gate set on PR + push to main,
  pinned action SHAs, least-privilege token, gitleaks over full history.
- **Secrets** — zero in the repo; `.env.example` documents the only secret
  (`GITHUB_TOKEN`, used solely for pushing this repo); `requirements.lock` is committed.
- **Algorithms** — every non-trivial algorithm is documented in `algorithms/`
  *before* code, with a machine-checkable line index (`make doc-index-check`).

## Repository layout

```
algorithms/    algorithm documents + INDEX.md registry
hooks/         committed git hooks
output/        the generated manual (committed — it is the deliverable)
scripts/       build_index.py (algorithm-doc index tool)
src/m21_crawl/ production code (one module per responsibility)
tests/         pytest suite mirroring src/ (network tests opt-in via -m live)
```

## Provenance

- Portal IDs, endpoint paths, and session flow were reverse-engineered from the
  portal's own bootstrap + application bundle (`application-bundle.min.js`).
- Fetched 2026-10-02; the output file records the exact fetch time and totals.
