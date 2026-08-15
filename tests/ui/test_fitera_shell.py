from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from excel_transform_1c.ui.app import create_app
from tests.helpers.workbooks import reference_bytes, workbook_bytes


pytestmark = pytest.mark.ui


def _client(tmp_path) -> TestClient:
    client = TestClient(create_app(tmp_path / "runtime"))
    for kind in ("erp_articles", "organizations", "scenarios"):
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


def test_fitera_shell_preserves_business_forms_and_safety_boundary(tmp_path):
    client = _client(tmp_path)
    response = client.get("/")

    assert response.status_code == 200
    assert 'class="brand-logo"' in response.text
    assert 'src="/static/fitera-logo.png"' in response.text
    assert "ООО «ФИТЭРА»" in response.text
    assert "LOCAL PREVIEW" in response.text
    assert "Запись в ERP и 1С отключена" in response.text
    assert "Проверьте справочники" in response.text
    assert "Выберите контекст и файл" in response.text
    assert "Получите preview и экспорт" in response.text
    assert 'data-testid="reference-form"' in response.text
    assert 'data-testid="scenario-form"' in response.text
    assert 'data-testid="process-form"' in response.text
    assert 'data-testid="organization-root"' in response.text
    assert 'data-testid="organization-node"' in response.text
    assert 'data-testid="scenario-select"' in response.text
    assert 'data-testid="all-year"' in response.text
    assert 'data-testid="process-submit"' in response.text
    assert 'accept=".xlsx,.xls,.xlsm"' in response.text
    assert "/static/app.css?v=" in response.text


def test_fitera_styles_include_responsive_and_accessible_states(tmp_path):
    client = _client(tmp_path)
    response = client.get("/static/app.css")

    assert response.status_code == 200
    assert "--green: #217346" in response.text
    assert ".brand-logo" in response.text
    assert ".safety-badge" in response.text
    assert ".workflow-overview" in response.text
    assert "button:disabled" in response.text
    assert "cursor: not-allowed" in response.text
    assert "input:focus-visible" in response.text
    assert "@media (max-width: 720px)" in response.text
    assert "overflow-wrap: anywhere" in response.text
    assert "prefers-reduced-motion" in response.text
    assert "@font-face" not in response.text


def test_preview_keeps_hooks_inside_fitera_result_shell(tmp_path):
    client = _client(tmp_path)
    scenario_id = client.app.state.workflow.store.list_scenarios()[0].scenario_id
    response = client.post(
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
                "synthetic.xlsx",
                workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert re.search(r"/runs/[a-f0-9]+", str(response.url))
    assert 'class="run-progress"' in response.text
    assert "Файл принят" in response.text
    assert "Preview построен" in response.text
    assert 'data-testid="preview-stats"' in response.text
    assert 'data-testid="preview-table"' in response.text
    assert 'data-testid="export-link"' in response.text
    assert "/static/run.js?v=" in response.text
