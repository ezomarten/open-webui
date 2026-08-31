"""Source-grep regression tests guarding the migration import-order fork wiring.

Upstream ``config.py`` calls ``run_migrations()`` at module import time
(mid-file), but ``migrations/env.py`` imports modules that in turn import
names defined later in ``config.py`` (e.g. ``ENABLE_LOCAL_WEB_FETCH``), so
every startup failed with 'Error running migrations' and Alembic upgrades
never applied. The fork defers the call to the bottom of the module so the
config module is fully initialized before migrations run. See FORK_NOTES.md,
maintenance record 2026-08-31.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '# fork:migration-import-order'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_config_runs_migrations_after_full_initialization():
    source = _read('backend', 'open_webui', 'config.py')

    call_site = source.index('if ENABLE_DB_MIGRATIONS:\n    run_migrations()')
    # A name defined late in config.py and required by migrations/env.py's
    # import chain (env.py -> models.calendar -> events -> retrieval.web.utils).
    late_definition = source.index('ENABLE_LOCAL_WEB_FETCH = (')
    assert call_site > late_definition, (
        'run_migrations() must be called after config.py is fully initialized'
    )


def test_config_carries_sentinel():
    source = _read('backend', 'open_webui', 'config.py')

    assert source.count(SENTINEL) >= 2
