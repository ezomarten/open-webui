# Fork Rules

This repository is a small-patch fork of Open WebUI. The goal is to stay close to upstream while preserving anonymous public-share behavior required by the deployment workspace.

## Preserve These Customizations

- Anonymous public share pages and APIs
- Snapshot-based public shares that do not require the owner session
- Public-share image attachment and public web citation support
- Browser TTS fallback on public pages
- Public-host `/pyodide/*` access
- Admin > General public-link settings backed by:
  - `ui.enable_public_chat_sharing`
  - `ui.public_share_base_url`

## Required Documentation Rule

Whenever fork-only behavior changes, update [FORK_FEATURES.md](FORK_FEATURES.md), [FORK_NOTES.md](FORK_NOTES.md), AND [fork-features.json](fork-features.json) in the same task. `FORK_FEATURES.md` is the human-readable feature catalog (one section per slug). `FORK_NOTES.md` is the workflow/timeline doc (Fork Management Contract, Pending Improvements, Maintenance Record, Upstream Base, Upstream Sync Checklist). `fork-features.json` is the machine-readable source of truth. The meta-test `backend/open_webui/test/util/test_fork_features_manifest.py` enforces that they stay in sync.

At minimum, keep these current:

- `FORK_FEATURES.md` (catalog: Goals, Feature Index, Feature Details, Public Host Allowlist, Current Limitations)
- `FORK_NOTES.md` > Current Operating Assumptions
- `FORK_NOTES.md` > Fork Management Contract
- `FORK_NOTES.md` > Pending Improvements
- `FORK_NOTES.md` > Maintenance Record Rules
- `FORK_NOTES.md` > Maintenance Record
- `FORK_NOTES.md` > Upstream Base
- `FORK_NOTES.md` > Upstream Sync Checklist

If the change is release-worthy, also update [CHANGELOG.md](CHANGELOG.md).

## Fork Wiring Test Rule

Whenever a fork-only customization is added, either:

1. Add a source-grep wiring test at `backend/open_webui/test/util/test_<slug>_wiring.py` that asserts every integration point still exists in source, AND tag each patch site with a `# fork:<slug>` / `<!-- fork:<slug> -->` / `// fork:<slug>` sentinel comment so the test can grep for the tag instead of a fragile substring; OR
2. Mark the manifest entry in [fork-features.json](fork-features.json) with `"pending_actions": ["add-wiring-test", "add-sentinel"]` and list the feature in the FORK_NOTES.md Pending Improvements section.

Before and after every upstream merge or replay, run:

```
pwsh ./scripts/verify-fork-wiring.ps1
```

A green BEFORE and red AFTER pinpoints exactly which fork patches were dropped by the sync.

## Required Cross-Workspace Rule

If a change affects deployment steps or which image should be running locally, update the workspace root [../README.md](../README.md) too.

## Local Apply Rule

- Local runtime testing depends on workspace root [.env](../.env) using `OPENWEBUI_IMAGE=open-webui-public-share`.
- If [.env](../.env) points at GHCR, local `docker build` results will not be visible after compose recreate.

## Secret Handling Rule

- Do not copy real secrets from [../.env](../.env) or local shell history into tracked files.
- Use placeholders in docs, examples, and committed config.

## Release And CI Rule

- Keep GitHub Release creation tag-only.
- Keep Docker publish fork-specific and single-image unless requirements explicitly change.
- Keep PyPI release disabled for normal fork pushes unless the fork release model changes.

## Translation Rule

If public-share or public-link UI strings change, update at least [src/lib/i18n/locales/ja-JP/translation.json](src/lib/i18n/locales/ja-JP/translation.json).
