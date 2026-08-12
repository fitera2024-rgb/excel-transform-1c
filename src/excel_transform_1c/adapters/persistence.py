from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from excel_transform_1c.core.models import Scenario


class LocalStore:
    def __init__(self, database: str | Path):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    scenario_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    erp_code TEXT,
                    comment TEXT NOT NULL DEFAULT '',
                    erp_confirmed INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(name, year)
                );
                CREATE TABLE IF NOT EXISTS reference_catalogs (
                    kind TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS manual_mappings (
                    mapping_key TEXT PRIMARY KEY,
                    erp_code TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS delegations (
                    user_key TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    PRIMARY KEY(user_key, node_id)
                );
                CREATE TABLE IF NOT EXISTS overrides (
                    run_id TEXT NOT NULL,
                    source_row INTEGER NOT NULL,
                    field TEXT NOT NULL,
                    original_value TEXT,
                    selected_value TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def list_scenarios(self) -> list[Scenario]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT scenario_id, name, year, erp_code, comment, erp_confirmed FROM scenarios ORDER BY year, name"
            ).fetchall()
        return [
            Scenario(
                scenario_id=row["scenario_id"],
                name=row["name"],
                year=row["year"],
                erp_code=row["erp_code"],
                comment=row["comment"],
                erp_confirmed=bool(row["erp_confirmed"]),
            )
            for row in rows
        ]

    def add_scenario(
        self,
        name: str,
        year: int,
        comment: str = "",
        erp_code: str | None = None,
        erp_confirmed: bool = False,
    ) -> Scenario:
        canonical = canonical_scenario_name(name, year)
        existing = next((item for item in self.list_scenarios() if item.name == canonical and item.year == year), None)
        if existing:
            return existing
        scenario = Scenario(
            scenario_id=uuid4().hex,
            name=canonical,
            year=year,
            erp_code=erp_code,
            comment=comment,
            erp_confirmed=erp_confirmed,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO scenarios(scenario_id, name, year, erp_code, comment, erp_confirmed) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    scenario.scenario_id,
                    scenario.name,
                    scenario.year,
                    scenario.erp_code,
                    scenario.comment,
                    int(scenario.erp_confirmed),
                ),
            )
        return scenario

    def replace_reference(self, kind: str, payload: list[dict[str, Any]]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reference_catalogs(kind, payload) VALUES (?, ?)
                ON CONFLICT(kind) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP
                """,
                (kind, json.dumps(payload, ensure_ascii=False)),
            )

    def load_reference(self, kind: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM reference_catalogs WHERE kind = ?", (kind,)).fetchone()
        return json.loads(row["payload"]) if row else []

    def save_manual_mapping(self, key: tuple[str, str, str, str], erp_code: str) -> None:
        encoded = json.dumps(key, ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO manual_mappings(mapping_key, erp_code) VALUES (?, ?)
                ON CONFLICT(mapping_key) DO UPDATE SET erp_code=excluded.erp_code, updated_at=CURRENT_TIMESTAMP
                """,
                (encoded, erp_code),
            )

    def load_manual_mappings(self) -> dict[tuple[str, str, str, str], str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT mapping_key, erp_code FROM manual_mappings").fetchall()
        return {tuple(json.loads(row["mapping_key"])): row["erp_code"] for row in rows}

    def set_delegations(self, user_key: str, node_ids: list[str]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM delegations WHERE user_key = ?", (user_key,))
            connection.executemany(
                "INSERT INTO delegations(user_key, node_id) VALUES (?, ?)",
                [(user_key, node_id) for node_id in dict.fromkeys(node_ids)],
            )

    def get_delegations(self, user_key: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT node_id FROM delegations WHERE user_key = ? ORDER BY node_id", (user_key,)
            ).fetchall()
        return [row["node_id"] for row in rows]

    def save_override(
        self,
        run_id: str,
        source_row: int,
        field: str,
        original_value: str,
        selected_value: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO overrides(run_id, source_row, field, original_value, selected_value) VALUES (?, ?, ?, ?, ?)",
                (run_id, source_row, field, original_value, selected_value),
            )


def canonical_scenario_name(name: str, year: int) -> str:
    compact = " ".join(name.replace("_", " ").split())
    if compact == f"ПЛАН {year}":
        return f"ПЛАН {year}"
    return compact
