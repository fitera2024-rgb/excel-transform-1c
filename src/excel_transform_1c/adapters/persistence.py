from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from excel_transform_1c.core.models import Scenario


@dataclass(frozen=True)
class ImportStats:
    incoming: int
    added: int
    updated: int
    total: int


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
                CREATE TABLE IF NOT EXISTS cfo_mappings (
                    source_key TEXT PRIMARY KEY,
                    target_node_id TEXT NOT NULL,
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
                "SELECT scenario_id, name, year, erp_code, comment, erp_confirmed "
                "FROM scenarios ORDER BY CASE WHEN year = 0 THEN 1 ELSE 0 END, year, name"
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
        scenario, _, _ = self.upsert_scenario(
            name=name,
            year=year,
            comment=comment,
            erp_code=erp_code,
            erp_confirmed=erp_confirmed,
        )
        return scenario

    def upsert_scenario(
        self,
        name: str,
        year: int,
        comment: str = "",
        erp_code: str | None = None,
        erp_confirmed: bool = False,
    ) -> tuple[Scenario, bool, bool]:
        canonical = canonical_scenario_name(name, year)
        normalized_code = (erp_code or "").strip() or None
        normalized_comment = comment.strip()

        with self._connect() as connection:
            row = connection.execute(
                "SELECT scenario_id, name, year, erp_code, comment, erp_confirmed "
                "FROM scenarios WHERE name = ? AND year = ?",
                (canonical, year),
            ).fetchone()

            if row is None:
                scenario = Scenario(
                    scenario_id=uuid4().hex,
                    name=canonical,
                    year=year,
                    erp_code=normalized_code,
                    comment=normalized_comment,
                    erp_confirmed=bool(erp_confirmed or normalized_code),
                )
                connection.execute(
                    "INSERT INTO scenarios("
                    "scenario_id, name, year, erp_code, comment, erp_confirmed"
                    ") VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        scenario.scenario_id,
                        scenario.name,
                        scenario.year,
                        scenario.erp_code,
                        scenario.comment,
                        int(scenario.erp_confirmed),
                    ),
                )
                return scenario, True, False

            merged_code = normalized_code or row["erp_code"]
            merged_comment = normalized_comment or row["comment"]
            merged_confirmed = bool(row["erp_confirmed"]) or bool(
                erp_confirmed or merged_code
            )
            updated = (
                merged_code != row["erp_code"]
                or merged_comment != row["comment"]
                or merged_confirmed != bool(row["erp_confirmed"])
            )
            if updated:
                connection.execute(
                    "UPDATE scenarios "
                    "SET erp_code = ?, comment = ?, erp_confirmed = ? "
                    "WHERE scenario_id = ?",
                    (
                        merged_code,
                        merged_comment,
                        int(merged_confirmed),
                        row["scenario_id"],
                    ),
                )

            scenario = Scenario(
                scenario_id=row["scenario_id"],
                name=row["name"],
                year=row["year"],
                erp_code=merged_code,
                comment=merged_comment,
                erp_confirmed=merged_confirmed,
            )
            return scenario, False, updated

    def merge_scenarios(self, payload: list[dict[str, Any]]) -> ImportStats:
        added = 0
        updated = 0
        for item in payload:
            _, was_added, was_updated = self.upsert_scenario(
                name=str(item["name"]),
                year=int(item.get("year") or 0),
                comment=str(item.get("comment") or ""),
                erp_code=str(item.get("erp_code") or "") or None,
                erp_confirmed=bool(item.get("erp_code")),
            )
            added += int(was_added)
            updated += int(was_updated)
        return ImportStats(
            incoming=len(payload),
            added=added,
            updated=updated,
            total=len(self.list_scenarios()),
        )

    def replace_reference(self, kind: str, payload: list[dict[str, Any]]) -> None:
        """
        Persist one global local reference catalog.

        The first upload creates the catalog. Later uploads supplement/update it
        by stable code and never create a per-organization copy.
        """
        key_field = {
            "erp_articles": "code",
            "organizations": "code",
            "intalev_cfos": "source_key",
        }.get(kind)
        if key_field is None:
            self._write_reference(kind, payload)
            return
        self.merge_reference(kind, payload, key_field=key_field)

    def merge_reference(
        self,
        kind: str,
        payload: list[dict[str, Any]],
        *,
        key_field: str,
    ) -> ImportStats:
        existing = self.load_reference(kind)
        ordered_keys: list[str] = []
        merged: dict[str, dict[str, Any]] = {}

        for item in existing:
            key = _reference_key(item, key_field)
            if not key or key in merged:
                continue
            ordered_keys.append(key)
            merged[key] = item

        incoming_seen: set[str] = set()
        added = 0
        updated = 0
        for item in payload:
            key = _reference_key(item, key_field)
            if not key:
                raise ValueError(f"Справочник {kind} содержит запись без кода")
            if key in incoming_seen:
                raise ValueError(f"Справочник {kind} содержит повторяющийся код: {key}")
            incoming_seen.add(key)

            if key not in merged:
                ordered_keys.append(key)
                merged[key] = item
                added += 1
            else:
                if merged[key] != item:
                    merged[key] = item
                    updated += 1

        combined = [merged[key] for key in ordered_keys]
        self._write_reference(kind, combined)
        return ImportStats(
            incoming=len(payload),
            added=added,
            updated=updated,
            total=len(combined),
        )

    def _write_reference(self, kind: str, payload: list[dict[str, Any]]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reference_catalogs(kind, payload) VALUES (?, ?)
                ON CONFLICT(kind) DO UPDATE
                SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP
                """,
                (kind, json.dumps(payload, ensure_ascii=False)),
            )

    def load_reference(self, kind: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM reference_catalogs WHERE kind = ?", (kind,)
            ).fetchone()
        return json.loads(row["payload"]) if row else []

    def save_manual_mapping(self, key: tuple[str, str, str, str], erp_code: str) -> None:
        encoded = json.dumps(key, ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO manual_mappings(mapping_key, erp_code) VALUES (?, ?)
                ON CONFLICT(mapping_key) DO UPDATE
                SET erp_code=excluded.erp_code, updated_at=CURRENT_TIMESTAMP
                """,
                (encoded, erp_code),
            )

    def load_manual_mappings(self) -> dict[tuple[str, str, str, str], str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT mapping_key, erp_code FROM manual_mappings"
            ).fetchall()
        return {
            tuple(json.loads(row["mapping_key"])): row["erp_code"]
            for row in rows
        }

    def save_cfo_mapping(self, source_key: str, target_node_id: str) -> None:
        self.save_cfo_mappings({source_key: target_node_id})

    def save_cfo_mappings(self, mappings: dict[str, str]) -> None:
        rows = [(key, value) for key, value in mappings.items()]
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO cfo_mappings(source_key, target_node_id) VALUES (?, ?)
                ON CONFLICT(source_key) DO UPDATE
                SET target_node_id=excluded.target_node_id, updated_at=CURRENT_TIMESTAMP
                """,
                rows,
            )

    def load_cfo_mappings(self) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT source_key, target_node_id FROM cfo_mappings"
            ).fetchall()
        return {row["source_key"]: row["target_node_id"] for row in rows}

    def set_delegations(self, user_key: str, node_ids: list[str]) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM delegations WHERE user_key = ?", (user_key,)
            )
            connection.executemany(
                "INSERT INTO delegations(user_key, node_id) VALUES (?, ?)",
                [(user_key, node_id) for node_id in dict.fromkeys(node_ids)],
            )

    def get_delegations(self, user_key: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT node_id FROM delegations WHERE user_key = ? ORDER BY node_id",
                (user_key,),
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
                "INSERT INTO overrides("
                "run_id, source_row, field, original_value, selected_value"
                ") VALUES (?, ?, ?, ?, ?)",
                (run_id, source_row, field, original_value, selected_value),
            )


def _reference_key(item: dict[str, Any], field: str) -> str:
    return str(item.get(field) or "").strip()


def canonical_scenario_name(name: str, year: int) -> str:
    compact = " ".join(name.replace("_", " ").split())
    if compact == f"ПЛАН {year}":
        return f"ПЛАН {year}"
    return compact
