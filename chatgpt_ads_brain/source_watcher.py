"""Offline source-change comparison; canonical claims are never auto-updated."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse


class SourceChangeState(StrEnum):
    SOURCE_UNCHANGED = "source_unchanged"
    SOURCE_CHANGED = "source_changed"


class ClaimReviewState(StrEnum):
    CLAIM_REVIEW_REQUIRED = "claim_review_required"
    CLAIM_RECONFIRMED = "claim_reconfirmed"
    CLAIM_AFFECTED = "claim_affected"
    CLAIM_CONTRADICTED = "claim_contradicted"
    CLAIM_SUPERSEDED = "claim_superseded"


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    url: str
    checked_at: datetime
    retrieved_at: datetime
    etag: str | None
    last_modified: str | None
    content_hash: str
    semantic_fingerprint: str
    refresh_policy: str


@dataclass(frozen=True, slots=True)
class SourceComparison:
    source_state: SourceChangeState
    claim_state: ClaimReviewState | None
    changed_metadata: tuple[str, ...]
    previous: SourceSnapshot
    current: SourceSnapshot


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")


def _semantic_text(content: bytes) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source content must be UTF-8") from exc
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"\w+", normalized, flags=re.UNICODE))


def build_snapshot(
    *,
    url: str,
    content: bytes,
    checked_at: datetime,
    retrieved_at: datetime,
    etag: str | None = None,
    last_modified: str | None = None,
    refresh_policy: str = "manual",
) -> SourceSnapshot:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("source URL must be an HTTPS URL without credentials")
    _aware(checked_at, "checked_at")
    _aware(retrieved_at, "retrieved_at")
    if checked_at < retrieved_at:
        raise ValueError("checked_at must not precede retrieved_at")
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    if not refresh_policy.strip():
        raise ValueError("refresh_policy must be non-empty")
    semantic = _semantic_text(content).encode("utf-8")
    return SourceSnapshot(
        url=url,
        checked_at=checked_at,
        retrieved_at=retrieved_at,
        etag=etag,
        last_modified=last_modified,
        content_hash=hashlib.sha256(content).hexdigest(),
        semantic_fingerprint=hashlib.sha256(semantic).hexdigest(),
        refresh_policy=refresh_policy,
    )


def compare_snapshots(previous: SourceSnapshot, current: SourceSnapshot) -> SourceComparison:
    if previous.url != current.url:
        raise ValueError("snapshots must refer to the same URL")
    compared = ("etag", "last_modified", "content_hash", "semantic_fingerprint", "refresh_policy")
    changed = tuple(field for field in compared if getattr(previous, field) != getattr(current, field))
    content_changed = previous.content_hash != current.content_hash
    semantic_changed = previous.semantic_fingerprint != current.semantic_fingerprint
    return SourceComparison(
        source_state=SourceChangeState.SOURCE_CHANGED if content_changed else SourceChangeState.SOURCE_UNCHANGED,
        claim_state=ClaimReviewState.CLAIM_REVIEW_REQUIRED if semantic_changed else None,
        changed_metadata=changed,
        previous=previous,
        current=current,
    )


def transition_claim_review(current: ClaimReviewState, target: ClaimReviewState) -> ClaimReviewState:
    allowed = {
        ClaimReviewState.CLAIM_RECONFIRMED,
        ClaimReviewState.CLAIM_AFFECTED,
        ClaimReviewState.CLAIM_CONTRADICTED,
        ClaimReviewState.CLAIM_SUPERSEDED,
    }
    if current is not ClaimReviewState.CLAIM_REVIEW_REQUIRED or target not in allowed:
        raise ValueError(f"invalid claim review transition: {current.value} -> {target.value}")
    return target
