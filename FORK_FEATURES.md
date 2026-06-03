# Fork Features Catalog

This file is the human-readable catalog of every fork-only customization carried on top of upstream Open WebUI. It complements:

- [`fork-features.json`](fork-features.json) — machine-readable source of truth (enforced by [`backend/open_webui/test/util/test_fork_features_manifest.py`](backend/open_webui/test/util/test_fork_features_manifest.py))
- [`FORK_NOTES.md`](FORK_NOTES.md) — maintenance timeline, release history, the Fork Management Contract, and upstream-sync checklist

Whenever a fork-only customization is added, changed, or removed, update this file in the same task as `fork-features.json` and `FORK_NOTES.md`.

## Goals

- Keep the main application protected behind an identity layer such as Cloudflare Access
- Serve anonymous public share pages from a separate host
- Keep the patch set small enough to rebase onto upstream releases

## Feature Index

| Slug                       | Summary                                                                                                                                                                                                                                           | Sentinel                        | Wiring test                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `public-share`             | Anonymous `/p/{public_share_id}` pages and `/api/v1/public-shares/*` APIs using snapshot-based shares                                                                                                                                             | `fork:public-share`             | [test_public_share_wiring.py](backend/open_webui/test/util/test_public_share_wiring.py)                       |
| `public-host-allowlist`    | Public-share host restricts routing to a small allowlist of static/public-share endpoints                                                                                                                                                         | `fork:public-host-allowlist`    | [test_public_share_wiring.py](backend/open_webui/test/util/test_public_share_wiring.py)                       |
| `public-link-settings`     | Admin > General `Enable Public Links` + `Public Link URL` (`ui.enable_public_chat_sharing`, `ui.public_share_base_url`)                                                                                                                           | `fork:public-link-settings`     | [test_public_share_wiring.py](backend/open_webui/test/util/test_public_share_wiring.py)                       |
| `openrouter-zdr`           | Optional `openrouter_zdr_only` per OpenRouter connection that switches discovery to `/endpoints/zdr` and forces `provider.zdr=true` on outgoing requests                                                                                          | `fork:openrouter-zdr`           | [test_openrouter_zdr_wiring.py](backend/open_webui/test/util/test_openrouter_zdr_wiring.py)                   |
| `about-disclosure`         | Settings > About disclosure that this deployment is a customized fork of Open WebUI                                                                                                                                                               | `fork:about-disclosure`         | [test_about_disclosure_wiring.py](backend/open_webui/test/util/test_about_disclosure_wiring.py)               |
| `settings-emphasis`        | Surface-aware hover/focus emphasis system and narrower content columns for Settings/Admin modals via `.ow-settings-*` classes                                                                                                                     | `fork:settings-emphasis`        | [test_settings_emphasis_wiring.py](backend/open_webui/test/util/test_settings_emphasis_wiring.py)             |
| `notes-md-import`          | Notes Markdown / `.txt` import with replace/append/insert-at-cursor modes, clipboard paste-as-Markdown / copy-as-Markdown helpers, mobile two-line layout                                                                                         | `fork:notes-md-import`          | [test_notes_md_import_wiring.py](backend/open_webui/test/util/test_notes_md_import_wiring.py)                 |
| `web-search-result-count`  | `WEB_SEARCH_RESULT_COUNT` enforced across the deduplicated combined result set during automatic web search                                                                                                                                        | `fork:web-search-result-count`  | [test_web_search_result_count_wiring.py](backend/open_webui/test/util/test_web_search_result_count_wiring.py) |
| `task-metadata-sanitize`   | Helper task endpoints force `params.function_calling="default"` and clear inherited `tool_ids`/`tool_servers`/`features`                                                                                                                          | `fork:task-metadata-sanitize`   | [test_task_metadata_wiring.py](backend/open_webui/test/util/test_task_metadata_wiring.py)                     |
| `responses-api-compat`     | Defensive response-content parsing plus Merge Responses frontend SSE parser for Chat Completions and Responses API payloads (LM Studio / Chutes compatibility)                                                                                    | `fork:responses-api-compat`     | [test_responses_api_compat_wiring.py](backend/open_webui/test/util/test_responses_api_compat_wiring.py)       |
| `chat-timeout-msg`         | Blank-exception-to-human-readable conversion, streamed timeout/stream-stall messaging, header cleanup, first-meaningful-chunk idle-timeout skip, direct `ClientTimeout` handoff to upstream requests, and `fetch_url` Web Loader timeout fallback | `fork:chat-timeout-msg`         | [test_chat_timeout_msg_wiring.py](backend/open_webui/test/util/test_chat_timeout_msg_wiring.py)               |
| `session-cleanup-lock`     | Session cleanup renews its Redis lock on a cadence shorter than the lock TTL to prevent worker churn on multi-worker deployments                                                                                                                  | `fork:session-cleanup-lock`     | [test_session_cleanup_lock_wiring.py](backend/open_webui/test/util/test_session_cleanup_lock_wiring.py)       |
| `env-changelog-unreleased` | `env.py` CHANGELOG parser tolerates an `Unreleased` heading without breaking imports or image builds                                                                                                                                              | `fork:env-changelog-unreleased` | [test_public_share_wiring.py](backend/open_webui/test/util/test_public_share_wiring.py)                       |

## Feature Details

### Anonymous public shares

Slugs: `public-share`, `public-host-allowlist`

- Adds `/p/{public_share_id}` pages and `/api/v1/public-shares/*` APIs for anonymous access
- Uses snapshot-based public shares so the public page does not require the owner session
- Keeps one active public share per chat
- The top-level app wiring for public shares remains intentionally explicit in `backend/open_webui/main.py`, `backend/open_webui/config.py`, and `src/lib/components/chat/ShareChatModal.svelte`, with source-level regression tests guarding against future upstream syncs silently dropping the feature integration again
- Public-share chat lookups in the create/get/delete routes explicitly await the async Chats model so public-link generation does not pass coroutine objects into snapshot building after the upstream async database migration
- Public-share snapshots now preserve the public user/assistant history tree so parallel multi-model responses render on anonymous pages instead of collapsing to only the current branch
- Public-share snapshot extraction also falls back from sanitized `history.messages` trees to the flattened `messages` list when saved history only contains non-public roles, which avoids false `No public messages found.` failures for still-visible chats

### Public page compatibility

Slug: `public-share`

- Public-share snapshots preserve image attachments and expose a share-scoped file content route
- Public-share snapshots also preserve public web citations so anonymous pages can show source links and preview snippets
- Public pages fall back to browser speech synthesis when authenticated TTS settings are unavailable
- Public pages can load `/pyodide/*` assets so browser-side Python execution continues to work
- Public-share responses and public-host `/p/*` pages add explicit noindex, nosniff, no-referrer, frame-deny, and public-page CSP headers, while the public page avoids credentialed static-asset fetches and third-party favicon lookups in read-only citation/search UI

### Admin-configurable public links

Slug: `public-link-settings`

- Admin > General includes `Enable Public Links` and `Public Link URL`
- Persistent config keys:
  - `ui.enable_public_chat_sharing`
  - `ui.public_share_base_url`
- `ENABLE_PUBLIC_CHAT_SHARING` and `PUBLIC_SHARE_BASE_URL` still work as initial env seeds, but saved admin settings take precedence after startup

### OpenRouter Zero Retention connections

Slug: `openrouter-zdr`

- Admin and direct connection settings include an optional `openrouter_zdr_only` flag for OpenRouter-backed connections
- When enabled, model discovery switches from `/api/v1/models` to `/api/v1/endpoints/zdr`
- Proxied chat, responses, legacy proxy requests, and browser-side direct chat requests also force `provider.zdr=true` for that connection

### About disclosure

Slug: `about-disclosure`

- Settings > About includes a fork disclosure that states this deployment is a customized fork of Open WebUI and is not affiliated with or maintained by the official Open WebUI team

### Settings modal usability

Slug: `settings-emphasis`

- Chat settings, chat Controls section headers, advanced parameter panels, and admin settings now use a shared but surface-aware hover/focus system plus narrower desktop content columns so widely spaced label/control pairs stay grouped while editing in both light and dark themes; modal light-theme rows intentionally use stronger emphasis than admin rows, and explicit opt-in wrappers avoid flex-column layout regressions on admin forms
- Admin Settings > Connections now opts saved OpenAI/Ollama connection rows into that same emphasis treatment, and workspace model prompt-suggestion editors keep the prompt field top-aligned instead of centering it beside the title inputs

### Notes markdown import

Slug: `notes-md-import`

- Notes now include a dedicated Markdown import action for existing notes that converts external `.md` files into the rich-text note format instead of inserting raw markdown text
- Shared note creation/import helpers now normalize markdown into note-ready HTML, so imported markdown previews render correctly from both the notes list import flow and URL/query based note creation
- Markdown file detection now accepts common `.md`-style extensions even when browsers report `text/plain` or an empty MIME type, which commonly happens on Windows
- The note menu now groups import actions by format and insertion mode, supporting replace, append-to-end, and insert-at-cursor for Markdown and plain text imports, plus clipboard actions for paste-as-Markdown and copy-as-Markdown; nested submenus now stay open correctly while moving the pointer into third-level menu content, and root dropdown outside-click guards no longer swallow clicks on portaled submenu actions
- Clipboard paste follow-ups now insert at a stable saved ProseMirror range instead of depending on editor refocus, treat append-to-end on an empty note as a replace operation so Chromium-family browsers no longer throw a misleading clipboard-read failure, move `Access` into the note overflow menu, stack the note header on narrow screens so the title field keeps usable width, and clamp nested submenu placement within the viewport so `Download` / `Clipboard` menus stay visible on phone-width layouts
- Notes list rows now switch to a mobile-first two-line layout that gives the title most of the row width on narrow screens, keeps the updated-time label visible, and truncates only the creator label when space runs short

### Web search result limiting

Slug: `web-search-result-count`

- When web search query generation is enabled, automatic web search now enforces `WEB_SEARCH_RESULT_COUNT` across the combined deduplicated result set before loading pages or injecting snippet-only context

### Helper task metadata sanitization

Slug: `task-metadata-sanitize`

- Internal helper task endpoints override inherited request metadata so native function-calling chats do not leak builtin tool exposure into title, follow-up, tags, query, image-prompt, autocomplete, emoji, or MOA helper calls
- Helper tasks force `params.function_calling="default"` and clear inherited `tool_ids`, `tool_servers`, and `features`

### Responses API compatibility

Slug: `responses-api-compat`

- Upstream `v0.9.5` continues to cover the previously forked Responses API task-normalization and native tool-loop fixes that were needed for Gemini and LM Studio-compatible providers
- This fork keeps the more defensive response-content parsing and timing/error hardening that protects task helpers and streamed post-processing across chat-completions-style and Responses-style payloads
- Merge Responses now also parses Responses API SSE events on the frontend, so LM Studio-style local connections that stream `response.output_text.delta` / `response.completed` no longer fail MOA merges solely because the merge parser expected Chat Completions deltas
- Merge Responses now asks the MOA task endpoint for non-stream JSON completions and extracts the normalized final assistant content from that response, which sidesteps Chutes/OpenAI-compatible reasoning models whose streamed merge responses emit long `reasoning_content` traces before completion but never provide usable `delta.content` tokens to the merge UI

### Chat timeout error messaging

Slug: `chat-timeout-msg`

- Chat processing now converts blank exception strings into human-readable error content before saving or emitting `chat:message:error`
- Streamed upstream timeout failures now surface as an explicit timeout or stream-stall message instead of an empty red error banner
- The generic streamed response wrapper now also persists and emits that timeout text when the failure happens during streamed response iteration, so stored `error.content` remains populated for the affected assistant message
- OpenAI-compatible and Ollama streaming upstream requests now wait for the first meaningful upstream output chunk without applying the idle timeout, ignoring role-only deltas and Responses API status preludes such as `response.created` / `response.in_progress` before the timeout starts; non-stream requests continue to use the configured total request timeout
- OpenAI-compatible streamed proxy responses also strip stale `Content-Encoding`, `Content-Length`, and `Transfer-Encoding` headers after aiohttp auto-decompression so downstream chat responses do not fail on the upstream proxy cleanup path
- Native `fetch_url` tool calls now cap page loading with the configured Web Loader timeout when available and otherwise fall back to a 30-second budget, so slow pages fail with a visible tool error instead of leaving chats stuck in `fetch_url`

### Multi-worker session cleanup stability

Slug: `session-cleanup-lock`

- Session cleanup now renews its Redis lock on a cadence shorter than the lock TTL, preventing avoidable worker churn from lock-renew failures during long-lived chats on multi-worker deployments

### CHANGELOG `Unreleased` tolerance

Slug: `env-changelog-unreleased`

- `backend/open_webui/env.py` reads `CHANGELOG.md` to derive `WEBUI_VERSION`. The fork's variant tolerates an `Unreleased` heading at the top of the file (skipping it when picking the latest released version) so commits between releases do not break imports or image builds.

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
