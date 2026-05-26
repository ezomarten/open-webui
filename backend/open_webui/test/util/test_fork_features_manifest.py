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


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding='utf8'))


def _load_fork_notes() -> str:
    return FORK_NOTES_PATH.read_text(encoding='utf8')


def test_manifest_file_exists_and_parses():
    manifest = _load_manifest()
    assert manifest.get('schema_version') == 1
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


def test_declared_wiring_tests_actually_exist():
    manifest = _load_manifest()
    for feature in manifest['fork_features']:
        wiring_test = feature['wiring_test']
        if wiring_test is None:
            continue
        path = REPO_ROOT / wiring_test
        assert path.exists(), (
            f'feature {feature["slug"]!r} declares wiring_test {wiring_test!r} ' f'but the file is missing'
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
                f'feature {feature["slug"]!r} has pending actions {pending} but is ' f'not mentioned in FORK_NOTES.md'
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
