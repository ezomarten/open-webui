# Fork Notes

This fork now tracks Open WebUI `v0.9.0` and carries a small set of deployment-focused customizations for anonymous public sharing.

## Goals

- Keep the main application protected behind an identity layer such as Cloudflare Access
- Serve anonymous public share pages from a separate host
- Keep the patch set small enough to rebase onto upstream releases

## Current Operating Assumptions

- Protected host: `https://openwebui.localhost`
- Anonymous public-share host: `https://public-openwebui.localhost`
- Deployment workspace operator runbook lives in [../README.md](../README.md)
- Local rebuilds only affect runtime when workspace root [../.env](../.env) sets `OPENWEBUI_IMAGE=open-webui-public-share` or another local `open-webui-public-share[:tag]` reference
- If [../.env](../.env) points to a GHCR tag, compose recreate will continue to run the GHCR image even after a successful local `docker build`
- Current published GHCR baseline remains `0.8.12-publicshare.1` until `0.9.0-publicshare.1` is pushed
- Current local fork head should be treated as the source of truth for future local image rebuilds
- Multi-worker deployments must set `REDIS_URL` as well as `WEBSOCKET_REDIS_URL`; the latter only covers Socket.IO, while the former is required for AppConfig persistent-config sync so admin connection settings do not revert across workers
- Before pushing a release commit or tag, run `python scripts/release_preflight.py` from an environment that has the repo's Python and Node dependencies installed
- For GHCR pushes from GitHub Actions, either grant the package Actions access for this repository or configure repository secrets `GHCR_USERNAME` and `GHCR_TOKEN`; otherwise `docker/build-push-action` can fail with `403 Forbidden` on blob HEAD requests even when login succeeds with `GITHUB_TOKEN`

## Included Customizations

### Anonymous public shares

- Adds `/p/{public_share_id}` pages and `/api/v1/public-shares/*` APIs for anonymous access
- Uses snapshot-based public shares so the public page does not require the owner session
- Keeps one active public share per chat
- Public-share snapshots now preserve the public user/assistant history tree so parallel multi-model responses render on anonymous pages instead of collapsing to only the current branch

### Public page compatibility

- Public-share snapshots preserve image attachments and expose a share-scoped file content route
- Public-share snapshots also preserve public web citations so anonymous pages can show source links and preview snippets
- Public pages fall back to browser speech synthesis when authenticated TTS settings are unavailable
- Public pages can load `/pyodide/*` assets so browser-side Python execution continues to work
- Public-share responses and public-host `/p/*` pages add explicit noindex, nosniff, no-referrer, frame-deny, and public-page CSP headers, while the public page avoids credentialed static-asset fetches and third-party favicon lookups in read-only citation/search UI

### Admin-configurable public links

- Admin > General includes `Enable Public Links` and `Public Link URL`
- Persistent config keys:
  - `ui.enable_public_chat_sharing`
  - `ui.public_share_base_url`
- `ENABLE_PUBLIC_CHAT_SHARING` and `PUBLIC_SHARE_BASE_URL` still work as initial env seeds, but saved admin settings take precedence after startup

### OpenRouter Zero Retention connections

- Admin and direct connection settings include an optional `openrouter_zdr_only` flag for OpenRouter-backed connections
- When enabled, model discovery switches from `/api/v1/models` to `/api/v1/endpoints/zdr`
- Proxied chat, responses, legacy proxy requests, and browser-side direct chat requests also force `provider.zdr=true` for that connection

### About disclosure

- Settings > About includes a fork disclosure that states this deployment is a customized fork of Open WebUI and is not affiliated with or maintained by the official Open WebUI team

### Web search result limiting

- When web search query generation is enabled, automatic web search now enforces `WEB_SEARCH_RESULT_COUNT` across the combined deduplicated result set before loading pages or injecting snippet-only context

### Helper task metadata sanitization

- Internal helper task endpoints override inherited request metadata so native function-calling chats do not leak builtin tool exposure into title, follow-up, tags, query, image-prompt, autocomplete, emoji, or MOA helper calls
- Helper tasks force `params.function_calling="default"` and clear inherited `tool_ids`, `tool_servers`, and `features`

### Responses API compatibility

- Upstream `v0.9.0` continues to cover the previously forked Responses API task-normalization and native tool-loop fixes that were needed for Gemini and LM Studio-compatible providers
- This fork keeps the more defensive response-content parsing and timing/error hardening that protects task helpers and streamed post-processing across chat-completions-style and Responses-style payloads

### Chat timeout error messaging

- Chat processing now converts blank exception strings into human-readable error content before saving or emitting `chat:message:error`
- Streamed upstream timeout failures now surface as an explicit timeout or stream-stall message instead of an empty red error banner
- The generic streamed response wrapper now also persists and emits that timeout text when the failure happens during streamed response iteration, so stored `error.content` remains populated for the affected assistant message
- OpenAI-compatible and Ollama streaming upstream requests now wait for the first meaningful upstream output chunk without applying the idle timeout, ignoring role-only deltas and Responses API status preludes such as `response.created` / `response.in_progress` before the timeout starts; non-stream requests continue to use the configured total request timeout

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

- Public shares only expose sanitized user/assistant history; non-public roles are collapsed out of the visible tree and older pre-v4 links need `Update and Copy Public Link` to regenerate the snapshot
- Image attachments and public web citations are included, but other file types and private citations remain excluded
- Public-link generation requires both a valid absolute `PUBLIC_SHARE_BASE_URL` and `Enable Public Links` turned on
- OpenRouter Zero Retention model discovery collapses endpoint variants by `model_id`, keeping provider names and tags as metadata on the merged entry

## Maintenance Record Rules

Whenever a fork-only customization is added, changed, or removed, update this file in the same task.

Each update should keep the following current:

- `Included Customizations`
- `Current Operating Assumptions`
- `Maintenance Record`
- `Upstream Base`
- `Upstream Sync Checklist`

Each maintenance entry should include:

- date
- intent
- key files or areas touched
- validation that was actually performed

If the change affects deployment behavior, also update [../README.md](../README.md).

If the change is release-worthy, also update [CHANGELOG.md](CHANGELOG.md).

If the change affects public-share or public-link UI strings, also update [src/lib/i18n/locales/ja-JP/translation.json](src/lib/i18n/locales/ja-JP/translation.json).

## Maintenance Record

- 2026-04-21: merged upstream `v0.9.0` into the fork mainline on a temporary worktree, re-applied the current uncommitted fork changes, and adapted public-share/timeout behavior to upstream's async database and shared `aiohttp` session-pool architecture while keeping public-link/public-share behavior intact; key files: `CHANGELOG.md`, `FORK_NOTES.md`, `README.md`, `backend/open_webui/internal/db.py`, `backend/open_webui/main.py`, `backend/open_webui/models/chats.py`, `backend/open_webui/models/public_shares.py`, `backend/open_webui/routers/ollama.py`, `backend/open_webui/routers/openai.py`, `backend/open_webui/routers/public_shares.py`, `backend/open_webui/utils/asgi_middleware.py`, `backend/open_webui/utils/http_timeouts.py`, `backend/open_webui/utils/public_share.py`, `backend/open_webui/utils/session_pool.py`, `src/lib/components/chat/ShareChatModal.svelte`, and `src/routes/p/[id]/+page.svelte`; validation: `git diff --cached --check`, `PYTHONPATH=backend c:/Users/it/openwebui/.venv/Scripts/python.exe -m pytest backend/open_webui/test/util/test_http_timeouts.py backend/open_webui/test/util/test_public_share.py backend/open_webui/test/util/test_error_handling.py -q` with `27 passed`, plus VS Code static diagnostics showing no errors in `backend/open_webui/main.py` and `backend/open_webui/utils/asgi_middleware.py`
- 2026-04-10: fixed OpenRouter-backed Merge Responses hangs where upstream kept an SSE connection alive with repeated `: OPENROUTER PROCESSING` comments but never produced a meaningful output chunk; the backend now enforces the configured timeout across the pre-content phase as wall-clock time instead of waiting forever for the first meaningful chunk, and the chat UI clears stale empty merged placeholders both after abandoned attempts and when an empty stream terminates without content. Key files: `backend/open_webui/utils/http_timeouts.py`, `backend/open_webui/utils/misc.py`, `backend/open_webui/test/util/test_http_timeouts.py`, `src/lib/components/chat/Chat.svelte`, `CHANGELOG.md`; validation: reproduced hanging MOA stream against chat `ff33c5a4-fa9c-435d-8ae5-ede80ee63cd0`, ran targeted pytest `backend/open_webui/test/util/test_http_timeouts.py`, and static error scan on the edited Chat.svelte file
- 2026-04-10: changed public-share snapshots from current-branch-only export to full sanitized public history trees so anonymous `/p/{id}` pages can render parallel multi-model responses with the existing MultiResponse UI; key files: `backend/open_webui/utils/public_share.py`, `backend/open_webui/models/public_shares.py`, `backend/open_webui/routers/public_shares.py`, `backend/open_webui/test/util/test_public_share.py`, `src/routes/p/[id]/+page.svelte`, `CHANGELOG.md`, `FORK_NOTES.md`; validation: targeted pytest for `backend/open_webui/test/util/test_public_share.py`
- 2026-04-09: fixed chat Merge Responses so `/api/v1/tasks/moa/completions` failures are normalized at the frontend API layer, surfaced via a visible toast that includes provider detail when available, and clear the transient merged-response loading state instead of silently leaving users guessing; key files: `src/lib/apis/index.ts`, `src/lib/components/chat/Chat.svelte`, `src/lib/i18n/locales/ja-JP/translation.json`, `CHANGELOG.md`; validation: attempted frontend `npm run check` but the repo still has pre-existing global type errors (`9059 errors`, `249 warnings`, `364 files`), while the check output did not reference the edited files and VS Code static diagnostics reported no new errors in `src/lib/apis/index.ts` or `src/lib/i18n/locales/ja-JP/translation.json`
- 2026-04-09: hardened anonymous public-share pages to look less suspicious to web-security scanners by adding explicit public-host/public-share response headers, removing credentialed static-asset fetches from the SPA shell, lazy-loading Socket.IO and Pyodide only when needed, and avoiding third-party favicon requests in read-only citation/search UI; key files: `backend/open_webui/utils/public_share_security.py`, `backend/open_webui/main.py`, `backend/open_webui/routers/public_shares.py`, `backend/open_webui/test/util/test_public_share.py`, `src/app.html`, `src/routes/+layout.svelte`, `src/lib/components/chat/Messages/Citations.svelte`, `src/lib/components/chat/Messages/ResponseMessage.svelte`, `src/lib/components/chat/Messages/ResponseMessage/StatusHistory.svelte`, `src/lib/components/chat/Messages/ResponseMessage/StatusHistory/StatusItem.svelte`, `src/lib/components/chat/Messages/ResponseMessage/WebSearchResults.svelte`, `src/lib/components/chat/Messages/Citations/CitationModal.svelte`, `CHANGELOG.md`; validation: targeted pytest for `backend/open_webui/test/util/test_public_share.py` plus frontend `npm run check`
- 2026-04-05: fixed admin Settings > Connections so edited connection payloads are written back into parent state before save, and aligned the deployment compose/runbook with multi-worker persistent-config requirements by wiring `REDIS_URL` alongside `WEBSOCKET_REDIS_URL`; key files: `src/lib/components/admin/Settings/Connections.svelte`, `../docker-compose.yml`, `../README.md`, `CHANGELOG.md`, `FORK_NOTES.md`; validation: `docker compose config` and static error scan on the edited Svelte file
- 2026-03-28: prepared fork release `0.8.12-publicshare.1` by updating release notes and published-image references, bumping package metadata to `0.8.12`, and fixing merge fallout in the terminal-server admin UI and backend verification route; key files: `CHANGELOG.md`, `FORK_NOTES.md`, `README.md`, `package.json`, `package-lock.json`, `backend/open_webui/routers/configs.py`, `src/lib/components/AddTerminalServerModal.svelte`; validation: `c:/Users/it/openwebui/.venv/Scripts/python.exe -m pytest backend/open_webui/test/util/test_task_metadata.py backend/open_webui/test/util/test_response_normalization.py backend/open_webui/test/util/test_http_timeouts.py backend/open_webui/test/util/test_error_handling.py backend/open_webui/test/util/test_openrouter_zdr.py backend/open_webui/test/util/test_public_share.py backend/open_webui/test/util/test_web_search.py -q` with `30 passed`, then `c:/Users/it/openwebui/.venv/Scripts/python.exe scripts/release_preflight.py` with Node `v22.22.1` forced to the front of `PATH`
- 2026-03-28: merged upstream `v0.8.12` into the fork mainline, retained the public-share/public-link/OpenRouter ZDR/timeout hardening/helper-task metadata patches, and kept upstream terminal-server verification proxying, file-list compatibility, and tool-embed rendering fixes; key files: `backend/open_webui/env.py`, `backend/open_webui/models/chats.py`, `backend/open_webui/models/files.py`, `backend/open_webui/retrieval/utils.py`, `backend/open_webui/retrieval/vector/dbs/oracle23ai.py`, `backend/open_webui/retrieval/vector/dbs/pgvector.py`, `backend/open_webui/routers/configs.py`, `backend/open_webui/utils/middleware.py`, `backend/open_webui/utils/models.py`, `pyproject.toml`, `src/lib/apis/configs/index.ts`, `src/lib/components/AddTerminalServerModal.svelte`, `src/lib/components/admin/Settings/Integrations.svelte`, `src/lib/components/chat/Settings/Integrations/Terminals.svelte`, `src/lib/components/chat/Settings/Integrations/Terminals/Connection.svelte`, `src/lib/components/common/ToolCallDisplay.svelte`, `src/lib/i18n/locales/*.json`; validation: `c:/Users/it/openwebui/.venv/Scripts/python.exe -m pytest backend/open_webui/test/util/test_task_metadata.py backend/open_webui/test/util/test_response_normalization.py backend/open_webui/test/util/test_http_timeouts.py backend/open_webui/test/util/test_error_handling.py backend/open_webui/test/util/test_openrouter_zdr.py backend/open_webui/test/util/test_public_share.py backend/open_webui/test/util/test_web_search.py -q` with `30 passed`, then `c:/Users/it/openwebui/.venv/Scripts/python.exe scripts/release_preflight.py` with Node `v22.22.1` forced to the front of `PATH`
- 2026-03-26: prepared fork release `0.8.11-publicshare.1` by converting the changelog entry from `Unreleased`, updating published-image references, regenerating i18n catalogs, and normalizing release-preflight formatting drift; key files: `CHANGELOG.md`, `README.md`, `FORK_NOTES.md`, `backend/open_webui/**`, `src/lib/i18n/locales/*.json`, `src/lib/components/chat/FileNav.svelte`, `src/lib/components/chat/FileNav/FilePreview.svelte`, `src/tailwind.css`, `docs/SECURITY.md`; validation: `python -m black --check backend`, `npm run check:format`, `npm run i18n:parse`, `npm run test:frontend`, and `npm run build`
- 2026-03-26: normalized the workspace update/publish scripts and runbooks around the canonical local image reference `open-webui-public-share`, while keeping GHCR examples explicit for published releases; key files: `../README.md`, `../update-openwebui.ps1`, `../update-openwebui-local.ps1`, `../publish-openwebui-image.ps1`, `README.md`, `FORK_NOTES.md`; validation: compared workspace [../.env](../.env) and [../docker-compose.yml](../docker-compose.yml) against the already completed local runtime verification where `docker inspect open-webui --format '{{.Config.Image}}'` returned `open-webui-public-share` and localhost returned `200 OK`
- 2026-03-26: merged upstream `v0.8.11` into the fork mainline, kept the public-share/public-link/OpenRouter ZDR/timeout hardening patches, and re-applied helper-task metadata sanitization so internal task helpers do not inherit native builtin tool exposure; key files: `Dockerfile`, `backend/open_webui/main.py`, `backend/open_webui/routers/auths.py`, `backend/open_webui/routers/channels.py`, `backend/open_webui/routers/ollama.py`, `backend/open_webui/routers/openai.py`, `backend/open_webui/routers/retrieval.py`, `backend/open_webui/routers/tasks.py`, `backend/open_webui/utils/middleware.py`, `backend/open_webui/utils/misc.py`, `backend/open_webui/utils/task_metadata.py`, `backend/open_webui/test/util/test_task_metadata.py`, `src/lib/components/chat/Settings/DataControls.svelte`, `src/lib/i18n/locales/ja-JP/translation.json`, `CHANGELOG.md`; validation: static error scan on all conflict-resolved files plus targeted pytest `open_webui/test/util/test_task_metadata.py open_webui/test/util/test_response_normalization.py open_webui/test/util/test_http_timeouts.py open_webui/test/util/test_error_handling.py open_webui/test/util/test_openrouter_zdr.py open_webui/test/util/test_public_share.py open_webui/test/util/test_web_search.py -q` with `30 passed`
- 2026-03-22: refined streamed upstream idle-timeout start conditions so OpenAI-compatible and Ollama requests ignore role-only deltas plus Responses API status preludes such as `response.created` / `response.in_progress` before starting the configured timeout window, which avoids false stream-stall failures while a model is still warming up or processing the prompt; key files: `backend/open_webui/utils/http_timeouts.py`, `backend/open_webui/utils/misc.py`, `backend/open_webui/routers/openai.py`, `backend/open_webui/routers/ollama.py`, `backend/open_webui/test/util/test_http_timeouts.py`, `README.md`, `docs/openwebui-empty-error-debug-repro.md`, `CHANGELOG.md`; validation: targeted pytest for `backend/open_webui/test/util/test_http_timeouts.py`, local image rebuild, `docker compose up -d --force-recreate open-webui`, and runtime verification against local LM Studio-backed `Local.qwen3-swallow-30b-a3b-rl-v0.2` / `Local.gpt-oss-swallow-20b-sft-v0.1_moe` models showing first stream events after ~19-21s and first content after ~25-45s without a pre-first-output 5-second disconnect
- 2026-03-22: switched OpenAI-compatible and Ollama streaming upstream requests from wall-clock total timeout handling to first-chunk wait plus post-first-chunk idle timeout handling, preserve explicit stream-stall text through the shared stream wrapper, and persist streamed timeout errors even when they are raised during response iteration; key files: `backend/open_webui/utils/http_timeouts.py`, `backend/open_webui/utils/misc.py`, `backend/open_webui/utils/middleware.py`, `backend/open_webui/routers/openai.py`, `backend/open_webui/routers/ollama.py`, `backend/open_webui/test/util/test_http_timeouts.py`, `backend/open_webui/test/util/test_error_handling.py`; validation: targeted pytest for timeout and error-handling helpers, local image rebuild, `docker compose up -d --force-recreate open-webui`, controlled mock OpenAI-compatible upstream repro, and direct verification that persisted `error.content` stored the explicit stream-stall message
- 2026-03-22: fixed blank chat error banners when upstream streamed requests exceed the configured timeout by converting empty exception strings into explicit timeout/error messages before persistence and websocket emission; key files: `backend/open_webui/utils/error_handling.py`, `backend/open_webui/main.py`, `backend/open_webui/test/util/test_error_handling.py`; validation: targeted pytest for the new helper
- 2026-03-20: published `ghcr.io/farefore/open-webui-public-share:0.8.10-publicshare.12` and moved `stable` to the same digest after fixing Responses API task normalization and streaming timing metadata; validation: `python scripts/release_preflight.py`, `pytest open_webui/test/util/test_web_search.py -q`, runtime helper assertions inside the rebuilt `open-webui` container, local image rebuild, `docker compose up -d --force-recreate open-webui`, `docker inspect open-webui --format '{{.Config.Image}} {{.Created}}'`, `curl.exe -I http://localhost:3000`, and GHCR push success
- 2026-03-20: fixed Responses API compatibility for task-driven query/image prompt generation and hardened streaming reasoning output timing so chats no longer fail with `'choices'` or `'started_at'`; key files: `backend/open_webui/utils/misc.py`, `backend/open_webui/routers/tasks.py`, `backend/open_webui/utils/middleware.py`, `backend/open_webui/routers/channels.py`, `backend/open_webui/test/util/test_response_normalization.py`, `CHANGELOG.md`; validation: `pytest open_webui/test/util/test_web_search.py -q`, runtime helper assertions inside the rebuilt `open-webui` container, local image rebuild, `docker compose up -d --force-recreate open-webui`, `docker inspect open-webui --format '{{.Config.Image}} {{.Created}}'`, and `curl.exe -I http://localhost:3000`
- 2026-03-19: added a shared Prettier format check to the repo release preflight after the `.10` release push still failed frontend formatting on `ManageOllama.svelte`; key files: `package.json`, `.github/workflows/format-build-frontend.yaml`, `scripts/release_preflight.py`, `src/lib/components/admin/Settings/Models/Manage/ManageOllama.svelte`; validation: `npm run check:format`, `python scripts/release_preflight.py`
- 2026-03-19: fixed automatic web search so generated multi-query searches respect the configured global result count before fetching pages or building snippet-only docs; key files: `backend/open_webui/routers/retrieval.py`, `backend/open_webui/utils/web_search.py`, `backend/open_webui/test/util/test_web_search.py`, `CHANGELOG.md`; validation: `pytest open_webui/test/util/test_web_search.py -q`
- 2026-03-19: fixed admin Settings > Models so Ollama management streams accept either raw JSON lines or SSE `data:` lines, avoiding intermittent `Unexpected token 'd'` parse failures; key files: `src/lib/components/admin/Settings/Models/Manage/ManageOllama.svelte`; validation: `npm run build`, user-confirmed runtime verification
- 2026-03-19: hardened release preflight after post-release Actions failures by aligning backend Black checks to Python 3.12, committing generated i18n catalogs, and adding `scripts/release_preflight.py`; key files: `.github/workflows/format-backend.yaml`, `.github/workflows/format-build-frontend.yaml`, `package.json`, `scripts/release_preflight.py`; validation: local `python -m black --check backend`, `npm run check:i18n`, `npm run test:frontend`, and `npm run build`
- 2026-03-19: published `ghcr.io/farefore/open-webui-public-share:0.8.10-publicshare.9` and moved `stable` to digest `sha256:9af0015f3e63ae585e3af2742aa947392d6cb2df2a748092bb535eccbe6a70a0`; validation: local rebuild, `pytest open_webui/test/util/test_openrouter_zdr.py -q`, `docker compose up -d --force-recreate open-webui`, `docker inspect open-webui --format '{{.Config.Image}}'`, `curl.exe -I http://localhost:3000`, user-confirmed ZDR behavior, and GHCR push success
- 2026-03-19: added an optional OpenRouter Zero Retention mode for admin and direct connections so model discovery can use `/api/v1/endpoints/zdr` and runtime requests force `provider.zdr=true`; key files: `backend/open_webui/routers/openai.py`, `backend/open_webui/utils/openrouter.py`, `backend/open_webui/test/util/test_openrouter_zdr.py`, `src/lib/components/AddConnectionModal.svelte`, `src/lib/apis/openai/index.ts`, `src/lib/apis/index.ts`, `src/routes/+layout.svelte`, `src/lib/i18n/locales/ja-JP/translation.json`, `CHANGELOG.md`; validation: `pytest open_webui/test/util/test_openrouter_zdr.py -q`
- 2026-03-16: updated GHCR publish workflow to support `GHCR_USERNAME`/`GHCR_TOKEN` secret fallback and documented the package access requirement after tag builds failed with blob HEAD `403 Forbidden`; key files: `.github/workflows/docker-build.yaml`, `CHANGELOG.md`; validation: GHCR secret provisioning and manual workflow dispatch
- 2026-03-15: added a Settings > About fork disclosure for license transparency without adding the notice to other app pages; key files: `src/lib/components/chat/Settings/About.svelte`, `src/lib/i18n/locales/ja-JP/translation.json`; validation: frontend type check
- 2026-03-15: hardened public-share image delivery to require owner-scoped file lookup and corrected share permission failures to return 403; key files: `backend/open_webui/routers/public_shares.py`; validation: `pytest open_webui/test/util/test_public_share.py -q`, local image rebuild, `docker compose up -d --force-recreate open-webui`, `docker inspect open-webui --format '{{.Config.Image}}'`, `curl.exe -I http://localhost:3000`, and container health reached `healthy`
- 2026-03-15: aligned GitHub Actions and release policy for this private fork; validation: local formatting/build checks plus green `Python CI` and `Frontend Build`
- 2026-03-15: added Japanese translations for public-share and public-link UI strings in [src/lib/i18n/locales/ja-JP/translation.json](src/lib/i18n/locales/ja-JP/translation.json); validation: local image rebuild plus runtime container inspection confirmed translated assets in the container
- 2026-03-15: clarified local deployment rule that workspace root [../.env](../.env) must point at the local image tag for local rebuilds to take effect; validation: `docker inspect open-webui --format '{{.Config.Image}}'` showed `open-webui-public-share:0.8.10-publicshare-local`
- 2026-03-15: added public-share support for public web citations while continuing to exclude private/file-backed citations; validation: backend sanitizer checks, local image rebuild, local `/p/{id}` verification, and operator-confirmed public-host verification

## Fork Release Summary

- `0.9.0-publicshare.1`: upstream `v0.9.0` sync, retained public-share/public-link/OpenRouter ZDR/timeout hardening patches, public-share snapshot files/citations/history, and merged upstream shared-chat access grants with the fork's snapshot-based public links
- `0.8.12-publicshare.1`: full upstream `v0.8.12` sync, retained public-share/public-link/OpenRouter ZDR/timeout hardening patches, helper-task metadata sanitization, and upstream terminal-server/file-list/tool-embed fixes
- `0.8.11-publicshare.1`: full upstream `v0.8.11` sync, retained public-share/public-link/OpenRouter ZDR/timeout hardening patches, and helper-task metadata sanitization for native function-calling chats
- `0.8.10-publicshare.13`: chat timeout error messaging hardening, streamed timeout persistence during response iteration, and meaningful-first-output timeout gating for OpenAI-compatible and Responses-style streams
- `0.8.10-publicshare.12`: Responses API task normalization and streaming timing metadata hardening
- `0.8.10-publicshare.11`: shared Prettier frontend formatting checks between release preflight and Frontend Build
- `0.8.10-publicshare.10`: web search result limiting, Ollama admin model stream parsing fix, and release preflight hardening
- `0.8.10-publicshare.9`: OpenRouter Zero Retention admin/direct connections, merged-model loading fix, and GHCR publish secret fallback release
- `0.8.10-publicshare.8`: About fork disclosure, public web citations in share snapshots, and owner-scoped public-share image delivery hardening
- `0.8.10-publicshare.7`: admin-managed public link settings
- `0.8.10-publicshare.6`: Pyodide assets allowed on the public host
- `0.8.10-publicshare.5`: image attachments included in public shares
- Earlier fork commits added anonymous public shares and public-page TTS hardening on top of upstream `v0.8.10`

## Upstream Base

Fork mainline now tracks upstream `v0.9.0`.

Retained fork-only areas on top of that base:

- anonymous public-share routes, snapshots, and the public-host allowlist
- public-link admin settings and related ja-JP strings
- OpenRouter Zero Retention admin/direct connection behavior
- streamed timeout and error-message hardening for upstream chat providers
- helper-task metadata sanitization for native function-calling chats

## Upstream Sync Checklist

When following a newer upstream Open WebUI release, verify at minimum:

1. public-share routes and snapshot logic still work for anonymous access
2. public-host allowlist behavior in backend entry routing is still intentionally narrow
3. public-share image delivery still works and remains image-only
4. public-page TTS fallback still avoids authenticated server-side TTS assumptions
5. `/pyodide/*` public-host access still works
6. admin public-link settings still persist via `ui.enable_public_chat_sharing` and `ui.public_share_base_url`
7. public-share snapshots still expose only public-safe citations and do not leak private/file-backed source metadata
8. Settings > About still shows a fork disclosure that explicitly says the deployment is a customized fork of Open WebUI and not official
9. public-link and public-share UI strings still have at least ja-JP translations when changed
10. OpenRouter admin and direct connections still optionally use `/api/v1/endpoints/zdr` and force `provider.zdr=true` when `openrouter_zdr_only` is enabled
11. workspace root [../README.md](../README.md) still matches the real deployment/apply procedure
12. automatic web search with generated queries still enforces `WEB_SEARCH_RESULT_COUNT` across the aggregated result set before loading pages or injecting snippet-only context
