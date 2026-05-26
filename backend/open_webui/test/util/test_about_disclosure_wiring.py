"""Source-grep regression test guarding the about-disclosure fork wiring.

The disclosure banner in ``Settings > About`` is required for license
compliance (Open WebUI BSD 3-Clause + commercial branding terms). It is
trivial for an upstream merge to silently delete the disclosure div from
``About.svelte`` because the surrounding section is heavily edited upstream.
This test enforces the sentinel comment and the canonical disclosure text.
See FORK_NOTES.md, maintenance record 2026-05-26 (frontend batch).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '<!-- fork:about-disclosure -->'

ABOUT_SVELTE = (
    'src',
    'lib',
    'components',
    'chat',
    'Settings',
    'About.svelte',
)


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_about_svelte_carries_sentinel():
    source = _read(*ABOUT_SVELTE)
    assert source.count(SENTINEL) >= 1


def test_about_svelte_renders_canonical_disclosure():
    source = _read(*ABOUT_SVELTE)
    assert 'role="note"' in source
    assert (
        'This deployment is a customized fork of Open WebUI. '
        'It is not affiliated with or maintained by the official Open WebUI team.'
    ) in source
