"""Tên topic theo contracts/mqtt/README.md: retailvision/v1/{site_id}/{device}/..."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topics:
    site_id: str
    edge_id: str = "edge01"
    node_id: str = "node01"

    @property
    def _prefix(self) -> str:
        return f"retailvision/v1/{self.site_id}"

    @property
    def state(self) -> str:
        return f"{self._prefix}/{self.edge_id}/state"

    @property
    def crossing(self) -> str:
        return f"{self._prefix}/{self.edge_id}/events/crossing"

    @property
    def alert(self) -> str:
        return f"{self._prefix}/{self.edge_id}/events/alert"

    @property
    def telemetry(self) -> str:
        return f"{self._prefix}/{self.edge_id}/telemetry"

    @property
    def edge_status(self) -> str:
        return f"{self._prefix}/{self.edge_id}/status"

    @property
    def settings_set(self) -> str:
        return f"{self._prefix}/{self.edge_id}/settings/set"

    @property
    def settings_result(self) -> str:
        return f"{self._prefix}/{self.edge_id}/settings/result"

    @property
    def operator_ack(self) -> str:
        return f"{self._prefix}/{self.node_id}/events/operator-ack"

    @property
    def node_status(self) -> str:
        return f"{self._prefix}/{self.node_id}/status"
