# Fork Rules

This repository is a small-patch fork of Open WebUI. The goal is to stay close to upstream while preserving anonymous public-share behavior required by the deployment workspace.

## Preserve These Customizations

- Anonymous public share pages and APIs
- Snapshot-based public shares that do not require the owner session
- Public-share image attachment support
- Browser TTS fallback on public pages
- Public-host `/pyodide/*` access
- Admin > General public-link settings backed by:
  - `ui.enable_public_chat_sharing`
  - `ui.public_share_base_url`

## Required Documentation Rule

Whenever fork-only behavior changes, update [FORK_NOTES.md](FORK_NOTES.md) in the same task.

At minimum, keep these sections current:

- `Included Customizations`
- `Current Operating Assumptions`
- `Maintenance Record Rules`
- `Maintenance Record`
- `Upstream Base`
- `Upstream Sync Checklist`

If the change is release-worthy, also update [CHANGELOG.md](CHANGELOG.md).

## Required Cross-Workspace Rule

If a change affects deployment steps or which image should be running locally, update the workspace root [../README.md](../README.md) too.

## Local Apply Rule

- Local runtime testing depends on workspace root [.env](../.env) using `OPENWEBUI_IMAGE=open-webui-public-share:0.8.10-publicshare-local`.
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