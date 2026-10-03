"""m21_crawl — crawler that builds the M21-1 manual in Markdown from VA Knowva.

Modules (one responsibility each):
  - config:   portal constants and endpoint paths
  - session:  anonymous session acquisition
  - client:   HTTP transport with retries and session refresh
  - tree:     topic-tree crawl (flatten, dedupe, order preservation)
  - articles: article listing and content fetch
  - mdconv:   rich HTML -> Markdown
  - assemble: ordered document assembly + completeness check
  - cli:      entrypoint orchestration
"""

__version__ = "0.1.0"
