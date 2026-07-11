"""Meta-test for the fork-features manifest.

The companion manifest at ``fork-features.json`` is the single source of
truth for which fork-only customizations exist and how they are guarded.
This test enforces the structural contract: every active feature must
carry the required metadata, every declared wiring test file must exist,
every pending action must be tracked in ``FORK_NOTES.md`` so it cannot
quietly disappear, and pending workflow improvements (e.g. the future
git-merge-based upstream sync) stay visible until they are completed.

See ``FORK_NOTES.md`` > Fork Management Contract for the human-readable
description of this contract.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MANIFEST_PATH = REPO_ROOT / 'fork-features.json'
FORK_NOTES_PATH = REPO_ROOT / 'FORK_NOTES.md'

VALID_PENDING_ACTIONS = {'add-wiring-test', 'add-sentinel'}
REQUIRED_FEATURE_KEYS = {
    'slug',
    'summary',
    'sentinel_tag',
    'wiring_test',
    'supporting_unit_tests',
    'notable_files',
    'status',
}
ALLOWED_FEATURE_STATUSES = {'active', 'removed'}
ALLOWED_GUARD_STYLES = {'sentinel', 'substring'}


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding='utf8'))


def _load_fork_notes() -> str:
    return FORK_NOTES_PATH.read_text(encoding='utf8')


def test_manifest_file_exists_and_parses():
    manifest = _load_manifest()
    assert manifest.get('schema_version') == 2
    assert isinstance(manifest.get('fork_features'), list) and manifest['fork_features']
    assert isinstance(manifest.get('pending_workflow_improvements'), list)


def test_feature_entries_have_required_shape():
    manifest = _load_manifest()
    seen_slugs: set[str] = set()
    seen_sentinels: set[str] = set()

    for feature in manifest['fork_features']:
        missing = REQUIRED_FEATURE_KEYS - feature.keys()
        assert not missing, f'feature missing keys {missing}: {feature}'

        slug = feature['slug']
        assert slug and slug.replace('-', '').isalnum(), f'invalid slug: {slug!r}'
        assert slug not in seen_slugs, f'duplicate slug: {slug!r}'
        seen_slugs.add(slug)

        sentinel = feature['sentinel_tag']
        assert sentinel.startswith('fork:'), f'sentinel must start with fork:: {sentinel!r}'
        assert sentinel not in seen_sentinels, f'duplicate sentinel: {sentinel!r}'
        seen_sentinels.add(sentinel)

        assert feature['status'] in ALLOWED_FEATURE_STATUSES, f'invalid status for {slug}: {feature["status"]!r}'

        assert isinstance(feature['supporting_unit_tests'], list)
        assert isinstance(feature['notable_files'], list)

        guard_style = feature.get('guard_style', 'sentinel')
        assert guard_style in ALLOWED_GUARD_STYLES, f'invalid guard_style for {slug}: {guard_style!r}'


def test_notable_files_exist_on_disk():
    """Every declared notable_file must exist. Upstream syncs frequently rename
    or delete files; an entry that no longer resolves is an early signal that a
    fork patch site moved (and may have been dropped) underneath the manifest."""
    manifest = _load_manifest()
    missing = []
    for feature in manifest['fork_features']:
        if feature['status'] != 'active':
            continue
        for nf in feature['notable_files']:
            if not (REPO_ROOT / nf).exists():
                missing.append(f'{feature["slug"]}: {nf}')
    assert not missing, (
        'notable_files reference paths that no longer exist (renamed/removed by '
        'an upstream sync?):\n  ' + '\n  '.join(missing)
    )


def test_active_features_keep_an_in_code_guard():
    """Each active feature must remain guarded in *product* code, not merely in
    docs or its own test. Sentinel-guarded features must have their
    ``fork:<slug>`` sentinel present in at least one non-test source file;
    substring-guarded features (which assert real code identifiers from their
    wiring test instead of a sentinel) are exempt but must declare
    ``"guard_style": "substring"`` so the exemption is explicit and a future
    maintainer cannot mistake an accidental sentinel loss for an intentional
    design choice.

    The scan covers the whole backend/frontend source tree (excluding tests and
    the non-code bookkeeping files) so that a patch which moved files during an
    upstream sync is still detected as present, while a fully *dropped* patch
    surfaces immediately as a failure here.
    """
    manifest = _load_manifest()

    scan_roots = [REPO_ROOT / 'backend' / 'open_webui', REPO_ROOT / 'src']
    source_exts = {'.py', '.ts', '.js', '.svelte', '.mjs', '.cjs'}
    blob_parts: list[str] = []
    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            if not path.is_file() or path.suffix not in source_exts:
                continue
            parts = {p.lower() for p in path.parts}
            if 'test' in parts or 'tests' in parts or path.name.startswith('test_'):
                continue  # never let a test's SENTINEL constant fake guard presence
            blob_parts.append(path.read_text(encoding='utf8', errors='ignore'))
    source_blob = '\n'.join(blob_parts)

    ungual = []
    for feature in manifest['fork_features']:
        if feature['status'] != 'active':
            continue
        if feature.get('guard_style', 'sentinel') == 'substring':
            continue
        tag = feature['sentinel_tag']
        if tag not in source_blob:
            ungual.append(
                f'{feature["slug"]}: sentinel {tag!r} not found in any non-test '
                f'source file; the patch may have been dropped, or mark the '
                f'feature "guard_style": "substring" if it is intentionally not '
                f'sentinel-guarded'
            )
    assert not ungual, 'fork features lost their in-code sentinel guard:\n  ' + '\n  '.join(ungual)


def test_declared_wiring_tests_actually_exist():
    manifest = _load_manifest()
    for feature in manifest['fork_features']:
        wiring_test = feature['wiring_test']
        if wiring_test is None:
            continue
        path = REPO_ROOT / wiring_test
        assert path.exists(), (
            f'feature {feature["slug"]!r} declares wiring_test {wiring_test!r} but the file is missing'
        )


def test_supporting_unit_tests_actually_exist():
    manifest = _load_manifest()
    for feature in manifest['fork_features']:
        for unit_test in feature['supporting_unit_tests']:
            path = REPO_ROOT / unit_test
            assert path.exists(), f'feature {feature["slug"]!r} references missing supporting test {unit_test!r}'


def test_pending_actions_are_well_formed_and_tracked():
    """A feature without a wiring test must declare it as a pending action."""
    manifest = _load_manifest()
    fork_notes = _load_fork_notes()
    assert '## Pending Improvements' in fork_notes, (
        'FORK_NOTES.md must contain a "## Pending Improvements" section so '
        'pending fork features and workflow improvements stay visible'
    )

    for feature in manifest['fork_features']:
        pending = feature.get('pending_actions', [])
        assert isinstance(pending, list)
        for action in pending:
            assert action in VALID_PENDING_ACTIONS, f'feature {feature["slug"]!r} has unknown pending action {action!r}'

        if feature['wiring_test'] is None:
            assert 'add-wiring-test' in pending, (
                f'feature {feature["slug"]!r} has no wiring_test and must declare '
                f'pending_actions=["add-wiring-test", ...]'
            )

        # Every pending feature slug must appear in FORK_NOTES Pending
        # Improvements so the human-readable doc never drifts from the
        # manifest. This catches "forgot to update FORK_NOTES" mistakes.
        if pending:
            assert feature['slug'] in fork_notes, (
                f'feature {feature["slug"]!r} has pending actions {pending} but is not mentioned in FORK_NOTES.md'
            )


def test_pending_workflow_improvements_are_tracked_in_fork_notes():
    manifest = _load_manifest()
    fork_notes = _load_fork_notes()
    for entry in manifest['pending_workflow_improvements']:
        assert {'id', 'summary', 'owner_doc', 'tracked_since'} <= entry.keys(), entry
        assert entry['id'] in fork_notes, (
            f'pending workflow improvement {entry["id"]!r} must be mentioned by id '
            f'in FORK_NOTES.md > Pending Improvements'
        )
