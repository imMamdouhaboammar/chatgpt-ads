"""Inspectable capability state and deterministic provider resolution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Protocol


class CapabilityStatus(StrEnum):
    SUPPORTED = "supported"
    NOT_VERIFIED = "not_verified"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    REQUIRES_NATIVE_EVIDENCE = "requires_native_evidence"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True, slots=True)
class CapabilityState:
    capability: str
    provider: str
    status: CapabilityStatus
    reason: str
    configured: bool = False
    account_verified: bool = False

    @property
    def usable(self) -> bool:
        return self.status is CapabilityStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CapabilityResolution:
    capability: str
    provider: str | None
    status: CapabilityStatus
    reason: str
    candidates: tuple[CapabilityState, ...]

    @property
    def usable(self) -> bool:
        return self.provider is not None


class CapabilityProvider(Protocol):
    provider: str

    def capabilities(self) -> Iterable[CapabilityState]: ...


class CapabilityResolver:
    """Resolve a capability without hiding why higher-priority paths failed."""

    PROVIDER_ORDER = (
        "host_native",
        "advertiser_api",
        "native_csv",
        "normalized_csv",
        "knowledge",
    )

    def __init__(self, providers: Iterable[CapabilityProvider]):
        order = {name: index for index, name in enumerate(self.PROVIDER_ORDER)}
        self._providers = sorted(providers, key=lambda item: (order.get(item.provider, len(order)), item.provider))

    def inspect(self, capability: str) -> tuple[CapabilityState, ...]:
        states = [state for provider in self._providers for state in provider.capabilities() if state.capability == capability]
        return tuple(states)

    def resolve(self, capability: str) -> CapabilityResolution:
        candidates = self.inspect(capability)
        for state in candidates:
            if state.usable:
                return CapabilityResolution(capability, state.provider, state.status, state.reason, candidates)
        if candidates:
            return CapabilityResolution(capability, None, candidates[0].status, "; ".join(f"{item.provider}: {item.reason}" for item in candidates), candidates)
        return CapabilityResolution(capability, None, CapabilityStatus.UNAVAILABLE, "no provider declared this capability", ())
