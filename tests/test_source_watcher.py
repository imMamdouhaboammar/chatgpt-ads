from __future__ import annotations

import unittest
from datetime import datetime, timezone

from chatgpt_ads_brain.source_watcher import (
    ClaimReviewState,
    SourceChangeState,
    build_snapshot,
    compare_snapshots,
    transition_claim_review,
)


class SourceWatcherTests(unittest.TestCase):
    def snapshot(self, content: bytes, **changes):
        values = {
            "url": "https://example.test/docs",
            "content": content,
            "checked_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "retrieved_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "etag": '"one"',
            "last_modified": "Wed, 01 Jan 2026 00:00:00 GMT",
            "refresh_policy": "weekly",
        }
        values.update(changes)
        return build_snapshot(**values)

    def test_unchanged_content_keeps_claims_out_of_review(self):
        previous = self.snapshot(b"Documented campaign reporting")
        current = self.snapshot(b"Documented campaign reporting", etag='"two"')
        result = compare_snapshots(previous, current)
        self.assertEqual(result.source_state, SourceChangeState.SOURCE_UNCHANGED)
        self.assertIsNone(result.claim_state)
        self.assertEqual(result.changed_metadata, ("etag",))

    def test_semantic_change_requires_review_without_overwriting_claims(self):
        previous = self.snapshot(b"Campaign reports clicks")
        current = self.snapshot(b"Campaign reports clicks and conversions")
        result = compare_snapshots(previous, current)
        self.assertEqual(result.source_state, SourceChangeState.SOURCE_CHANGED)
        self.assertEqual(result.claim_state, ClaimReviewState.CLAIM_REVIEW_REQUIRED)
        self.assertIn("content_hash", result.changed_metadata)
        self.assertIn("semantic_fingerprint", result.changed_metadata)

    def test_whitespace_only_change_is_detected_but_not_semantic(self):
        previous = self.snapshot(b"Campaign reports clicks")
        current = self.snapshot(b"Campaign   reports\nclicks")
        result = compare_snapshots(previous, current)
        self.assertEqual(result.source_state, SourceChangeState.SOURCE_CHANGED)
        self.assertIsNone(result.claim_state)
        self.assertEqual(result.changed_metadata, ("content_hash",))

    def test_claim_review_transitions_are_explicit(self):
        for target in (
            ClaimReviewState.CLAIM_RECONFIRMED,
            ClaimReviewState.CLAIM_AFFECTED,
            ClaimReviewState.CLAIM_CONTRADICTED,
            ClaimReviewState.CLAIM_SUPERSEDED,
        ):
            self.assertEqual(transition_claim_review(ClaimReviewState.CLAIM_REVIEW_REQUIRED, target), target)
        with self.assertRaises(ValueError):
            transition_claim_review(ClaimReviewState.CLAIM_RECONFIRMED, ClaimReviewState.CLAIM_AFFECTED)

    def test_snapshot_rejects_non_https_and_naive_timestamps(self):
        with self.assertRaises(ValueError):
            self.snapshot(b"content", url="http://example.test")
        with self.assertRaises(ValueError):
            self.snapshot(b"content", checked_at=datetime(2026, 1, 1))


if __name__ == "__main__":
    unittest.main()
