"""Role-scoped navigation controller with lazy page activation.

The existing widget keys and tab ordering are an explicit compatibility
contract for persisted Streamlit sessions and mobile/desktop users.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ecoscan.services.accounts import UserProfile
from ecoscan.ui.navigation import NavigationSpec, navigation_for


@dataclass(frozen=True)
class ActiveNavigation:
    spec: NavigationSpec
    tabs: Mapping[str, Any]
    role: str

    def open(self, name: str) -> bool:
        tab = self.tabs.get(name)
        return bool(tab is not None and tab.open)

    @property
    def campaign_required(self) -> bool:
        return any(self.open(name) for name in (
            self.spec.campaign, self.spec.account, "Gestão"
        ))


def build_navigation(st: Any, profile: UserProfile) -> ActiveNavigation:
    """Preserve the legacy tab key; do not mount hidden page controllers."""
    spec = navigation_for(admin=profile.is_admin)
    tabs = dict(zip(
        spec.tabs,
        st.tabs(spec.tabs, key="main_navigation_" + profile.role, on_change="rerun"),
    ))
    return ActiveNavigation(spec=spec, tabs=tabs, role=profile.role)
