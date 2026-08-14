from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from excel_transform_1c.ui.app import create_app
from tests.helpers.workbooks import reference_bytes, workbook_bytes


pytestmark = pytest.mark.ui


def _client(tmp_path) -> TestClient:
    client = TestClient(create_app(tmp_path / "runtime"))
    for kind in ("erp_articles", "organizations", "scenarios", "intalev_cfos"):
        response = client.post(
            "/references",
            data={"kind": kind},
            files={
                "reference_file": (
                    f"synthetic-{kind}.xlsx",
                    reference_bytes(kind),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
    return client


def _upload(client: TestClient, payload: bytes):
    scenario_id = client.app.state.workflow.store.list_scenarios()[0].scenario_id
    return client.post(
        "/uploads",
        data={
            "reporting_unit": "ПС",
            "organization_node_id": "ps",
            "scenario_id": scenario_id,
            "year": "2026",
            "period_selector_present": "1",
            "all_year": "1",
        },
        files={
            "budget_file": (
                "synthetic-source-cfo.xlsx",
                payload,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        follow_redirects=True,
    )


def _run_id(response) -> str:
    match = re.search(r"/runs/([a-f0-9]+)", str(response.url))
    assert match
    return match.group(1)


def test_unmatched_source_cfo_shows_two_explicit_selectors_and_can_be_confirmed(tmp_path):
    client = _client(tmp_path)
    response = _upload(
        client,
        workbook_bytes(cfo_error=False, second_cfo="Исходный отдел"),
    )
    run_id = _run_id(response)

    assert response.status_code == 200
    assert "Исходный ЦФО → ЦФО Инталев → узел 1С" in response.text
    assert "Исходный отдел" in response.text
    assert 'data-cfo-intalev' in response.text
    assert 'data-cfo-target' in response.text
    assert "Сопоставление заблокировано" not in response.text

    confirmed = client.post(
        f"/runs/{run_id}/map-cfo",
        data={
            "source_reporting_unit": "ПС",
            "source_cfo": "Исходный отдел",
            "intalev_source_key": "code:INT-CFO-2",
            "target_node_id": "other",
            "confirmed": "1",
        },
        follow_redirects=True,
    )
    assert confirmed.status_code == 200
    assert "Сопоставление ЦФО подтверждено" in confirmed.text
    assert "INT-CFO-2" in confirmed.text
    assert client.app.state.workflow.store.load_source_cfo_mappings()[
        ("ПС", "Исходный отдел")
    ] == "code:INT-CFO-2"


def test_bulk_source_cfo_payload_confirms_two_stage_mappings(tmp_path):
    client = _client(tmp_path)
    response = _upload(client, workbook_bytes(cfo_error=False, second_cfo="Исходный отдел"))
    run_id = _run_id(response)

    selections = [
        {
            "source_reporting_unit": "ПС",
            "source_cfo": "ЦФО 1",
            "intalev_source_key": "code:INT-CFO-1",
            "target_node_id": "cfo",
        },
        {
            "source_reporting_unit": "ПС",
            "source_cfo": "Исходный отдел",
            "intalev_source_key": "code:INT-CFO-2",
            "target_node_id": "other",
        },
    ]
    confirmed = client.post(
        f"/runs/{run_id}/confirm-filled-cfo",
        data={"confirmed": "1", "selections": json.dumps(selections, ensure_ascii=False)},
        follow_redirects=True,
    )

    assert confirmed.status_code == 200
    assert "Подтверждено новых сопоставлений ЦФО: 2" in confirmed.text
    mappings = client.app.state.workflow.store.load_source_cfo_mappings()
    assert mappings[("ПС", "ЦФО 1")] == "code:INT-CFO-1"
    assert mappings[("ПС", "Исходный отдел")] == "code:INT-CFO-2"
