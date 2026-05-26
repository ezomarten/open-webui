"""Source-grep regression test guarding the settings-emphasis fork wiring.

The ``.ow-settings-*`` CSS class system in ``src/app.css`` provides the
fork's hover/focus emphasis styling for the Settings UI. The classes are
applied across many consumer components. Upstream merges occasionally
delete the CSS block (because the surrounding ``:root`` is heavily edited
upstream) or strip the class usage from consumer markup. This test
guards both the CSS source of truth and a representative consumer.

See FORK_NOTES.md, maintenance record 2026-05-26 (frontend batch).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

CSS_SENTINEL = '/* fork:settings-emphasis */'
SVELTE_SENTINEL = '<!-- fork:settings-emphasis -->'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_app_css_carries_sentinel_and_class_definitions():
    source = _read('src', 'app.css')

    # Sentinel at both the :root variable block and the class definition block.
    assert source.count(CSS_SENTINEL) >= 2

    # CSS custom properties.
    assert '--ow-settings-hover-bg-light' in source
    assert '--ow-settings-hover-bg-dark' in source
    assert '--ow-settings-focus-bg-light' in source
    assert '--ow-settings-focus-bg-dark' in source

    # Class definitions consumers rely on.
    for cls in (
        '.ow-settings-surface',
        '.ow-settings-surface-admin',
        '.ow-settings-surface-modal',
        '.ow-settings-surface-compact',
        '.ow-settings-row',
        '.ow-settings-block',
        '.ow-settings-trigger',
    ):
        assert cls in source, f'missing class definition: {cls}'


def test_representative_consumer_uses_ow_settings_class():
    source = _read(
        'src',
        'lib',
        'components',
        'admin',
        'Settings',
        'Connections',
        'OllamaConnection.svelte',
    )
    assert SVELTE_SENTINEL in source
    assert 'ow-settings-row' in source
