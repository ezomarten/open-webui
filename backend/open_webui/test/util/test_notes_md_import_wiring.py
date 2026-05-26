"""Source-grep regression test guarding the notes-md-import fork wiring.

The fork exposes a richer note import flow than upstream:

  * ``src/lib/components/notes/utils.ts`` defines helpers
    ``readMarkdownFile``, ``readPlainTextFile`` and
    ``createNoteContentFromMarkdown``.
  * ``Notes.svelte`` uses ``readMarkdownFile`` + ``createNoteHandler`` to
    drive ``inputFilesHandler`` (mobile two-line layout in note cards).
  * ``NoteEditor.svelte`` uses both helpers (markdown/plain-text) for the
    NoteMenu's import / paste-as-markdown / copy-as-markdown actions.
  * ``Notes/NoteMenu.svelte`` declares the ``onImport``,
    ``onPasteMarkdown`` and ``onCopyMarkdown`` props that wire the
    submenu actions.

The v0.9.5 upstream sync silently deleted the helper-based call sites
even though the helpers themselves remained. This test guards both the
helper exports and the consumer call sites via sentinel comments and
import checks. See FORK_NOTES.md, maintenance record 2026-05-26
(frontend batch).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '// fork:notes-md-import'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_notes_utils_carries_sentinel_and_exports_helpers():
    source = _read('src', 'lib', 'components', 'notes', 'utils.ts')

    # Sentinel above isMarkdownFile, readMarkdownFile and readPlainTextFile.
    assert source.count(SENTINEL) >= 3

    for export in (
        'export const isMarkdownFile',
        'export const readMarkdownFile',
        'export const isPlainTextFile',
        'export const readPlainTextFile',
        'export const createNoteContentFromMarkdown',
        'export const createNoteHandler',
    ):
        assert export in source, f'missing helper export: {export}'


def test_notes_svelte_uses_helper_based_import_flow():
    source = _read('src', 'lib', 'components', 'notes', 'Notes.svelte')

    assert SENTINEL in source
    assert 'readMarkdownFile' in source
    assert 'createNoteHandler' in source

    # Helper-based handler must call readMarkdownFile, not the inline
    # FileReader/marked-parse fallback that regressed during the v0.9.5 sync.
    assert 'await readMarkdownFile(file)' in source
    assert "import { marked } from 'marked'" not in source


def test_note_editor_svelte_uses_markdown_and_plain_text_helpers():
    source = _read('src', 'lib', 'components', 'notes', 'NoteEditor.svelte')

    assert SENTINEL in source
    assert 'readMarkdownFile' in source
    assert 'readPlainTextFile' in source
    assert 'createNoteContentFromMarkdown' in source

    # Format-aware import dispatch must remain wired.
    assert (
        "format === 'markdown' ? await readMarkdownFile(file) : await readPlainTextFile(file)"
        in source
    )


def test_note_menu_exposes_import_props():
    source = _read(
        'src', 'lib', 'components', 'notes', 'Notes', 'NoteMenu.svelte'
    )

    assert SENTINEL in source
    assert 'export let onImport' in source
    assert 'export let onPasteMarkdown' in source
    assert 'export let onCopyMarkdown' in source
