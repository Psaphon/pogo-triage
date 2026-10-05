# Feature Requests: pogo-triage

Ideas deferred from v1. Each moves into `docs/DEVPLAN.md` as a `## Feature:` block when it's picked up.

- **Mega bench viability.** Only one mega can be active at a time. Flag a mega as redundant when an owned mega of a similar type and role outperforms it. Extends `mega_potential` from `scoring-engine`.
- **Team diversification.** Move raid teams from six duplicates toward six distinct species without exceeding a configurable Stardust budget. Builds on `team-builder`.
- **Scheduled runs.** A cron trigger (UTC) alongside manual `workflow_dispatch`. A gist edit can't trigger Actions, so this is the only automatic path.
- **Collection history across runs.** Track what changed between exports. Adds SQLite and state that needs backing up, so it breaks v1's stateless design.
- **Trade candidate ranking.** Rank trade candidates while respecting untradeable rules (shadows, most mythicals).
- **Weight-tuning view.** Compare verdict sets across config changes, so weight edits can be judged before they're adopted.
