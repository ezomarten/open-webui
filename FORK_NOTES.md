# Fork Notes

This fork is based on Open WebUI `v0.8.10` and carries a small set of deployment-focused customizations for anonymous public sharing.

## Goals

- Keep the main application protected behind an identity layer such as Cloudflare Access
- Serve anonymous public share pages from a separate host
- Keep the patch set small enough to rebase onto upstream releases

## Included Customizations

### Anonymous public shares

- Adds `/p/{public_share_id}` pages and `/api/v1/public-shares/*` APIs for anonymous access
- Uses snapshot-based public shares so the public page does not require the owner session
- Keeps one active public share per chat

### Public page compatibility

- Public-share snapshots preserve image attachments and expose a share-scoped file content route
- Public pages fall back to browser speech synthesis when authenticated TTS settings are unavailable
- Public pages can load `/pyodide/*` assets so browser-side Python execution continues to work

### Admin-configurable public links

- Admin > General includes `Enable Public Links` and `Public Link URL`
- Persistent config keys:
  - `ui.enable_public_chat_sharing`
  - `ui.public_share_base_url`
- `ENABLE_PUBLIC_CHAT_SHARING` and `PUBLIC_SHARE_BASE_URL` still work as initial env seeds, but saved admin settings take precedence after startup

## Public Host Allowlist

When a request arrives on the public share host derived from `PUBLIC_SHARE_BASE_URL`, the fork only allows the following routes:

- `GET /api/config`
- `GET /_app/*`
- `GET /static/*`
- `GET /manifest.json`
- `GET /opensearch.xml`
- `GET|HEAD /pyodide/*`
- `GET|HEAD /p/{public_share_id}` when public links are enabled
- `GET|HEAD /api/v1/public-shares/{public_share_id}` when public links are enabled
- `GET|HEAD /api/v1/public-shares/{public_share_id}/files/{file_id}/content` when public links are enabled

Other routes on the public host return `404`.

## Current Limitations

- Public shares expose the current branch transcript only
- Image attachments are included, but other file types and citations remain excluded
- Public-link generation requires both a valid absolute `PUBLIC_SHARE_BASE_URL` and `Enable Public Links` turned on

## Fork Release Summary

- `0.8.10-publicshare.7`: admin-managed public link settings
- `0.8.10-publicshare.6`: Pyodide assets allowed on the public host
- `0.8.10-publicshare.5`: image attachments included in public shares
- Earlier fork commits added anonymous public shares and public-page TTS hardening on top of upstream `v0.8.10`

## Upstream Base

Fork-only commits currently on top of upstream `v0.8.10`:

- `e481066ac` Add anonymous public share support
- `5cd166462` Fix TTS configuration handling and improve voice selection logic
- `b46c6c54f` Include images in public shares
- `90e60366c` Allow Pyodide assets on public shares
- `d46c3cf3f` Add admin settings for public links