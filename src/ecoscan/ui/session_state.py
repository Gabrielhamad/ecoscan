"""Typed access to analysis-only Streamlit state.

This adapter preserves existing widget and analysis keys. Identity/session
credentials remain owned by the authentication component.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping


ANALYSIS_RESULT = "last_analysis_result"
ANALYSIS_SIGNATURE = "last_analysis_signature"
ANALYSIS_SOURCE = "last_analysis_source"
HISTORY_SIGNATURE = "last_history_saved_signature"
INGESTION_RESULTS = "dataset_ingestion_results"


@dataclass
class AnalysisSession:
    """Narrow boundary around mutable analysis state, without caching credentials."""

    state: MutableMapping[str, Any]

    @property
    def last_result(self) -> Any | None:
        return self.state.get(ANALYSIS_RESULT)

    @property
    def last_source(self) -> str | None:
        return self.state.get(ANALYSIS_SOURCE)

    @property
    def last_signature(self) -> str | None:
        return self.state.get(ANALYSIS_SIGNATURE)

    @property
    def last_failure(self) -> dict[str, Any] | None:
        return self.state.get("last_analysis_failure")

    def record_failure(self, signature: str, source: str, public_error: dict[str, Any]) -> None:
        self.state[ANALYSIS_SIGNATURE] = signature
        self.state[ANALYSIS_SOURCE] = source
        self.state["last_analysis_failure"] = public_error

    def matches(self, signature: str) -> bool:
        return self.state.get(ANALYSIS_SIGNATURE) == signature

    def invalidate_analysis(self) -> None:
        for key in list(self.state):
            if key.startswith("confirmed_disposal_"):
                self.state.pop(key, None)
        for key in (ANALYSIS_RESULT, ANALYSIS_SIGNATURE, ANALYSIS_SOURCE, "last_analysis_failure"):
            self.state.pop(key, None)

    def record_analysis(self, signature: str, result: Any, source: str) -> None:
        self.state[ANALYSIS_RESULT] = result
        self.state[ANALYSIS_SIGNATURE] = signature
        self.state[ANALYSIS_SOURCE] = source

    def history_saved_for(self, signature: str) -> bool:
        return self.state.get(HISTORY_SIGNATURE) == signature

    def mark_history_saved(self, signature: str) -> None:
        self.state[HISTORY_SIGNATURE] = signature

    @property
    def capture_generation(self) -> int:
        return int(self.state.get("analysis_capture_generation", 0))

    def reset_capture(self) -> None:
        self.invalidate_analysis()
        self.state["analysis_capture_generation"] = self.capture_generation + 1

    @property
    def ingestion_results(self) -> list[dict[str, Any]]:
        return self.state.get(INGESTION_RESULTS, [])

    def record_ingestion(self, results: list[dict[str, Any]]) -> None:
        self.state[INGESTION_RESULTS] = results
