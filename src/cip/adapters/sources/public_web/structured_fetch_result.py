from __future__ import annotations

from dataclasses import dataclass

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.structured_state_capture import CapturedStructuredState


@dataclass(frozen=True, slots=True)
class StructuredPublicWebFetchResult(PublicWebFetchResult):
    structured_states: tuple[CapturedStructuredState, ...] = ()

    def __post_init__(self) -> None:
        if self.bytes_received < 0:
            raise ValueError("bytes_received cannot be negative")
        if self.bytes_received == 0 and self.body:
            object.__setattr__(self, "bytes_received", len(self.body))


def structured_states_for_result(
    result: PublicWebFetchResult,
) -> tuple[CapturedStructuredState, ...]:
    if isinstance(result, StructuredPublicWebFetchResult):
        return result.structured_states
    return ()
