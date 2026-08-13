from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from excel_transform_1c.application.service import WorkflowService
from excel_transform_1c.core.models import (
    OrganizationNode,
    REPORT_TYPE_CODE,
    REPORT_TYPE_NAME,
)


PACKAGE_DIR = Path(__file__).resolve().parent


def _organization_tree_context(
    nodes: list[OrganizationNode],
) -> tuple[list[dict[str, str]], list[dict[str, str | int]]]:
    """Build a stable pre-order tree for the two-stage business selector."""

    by_id = {node.node_id: node for node in nodes}
    source_order = {node.node_id: index for index, node in enumerate(nodes)}
    children: dict[str, list[OrganizationNode]] = defaultdict(list)
    roots: list[OrganizationNode] = []

    for node in nodes:
        if node.parent_id and node.parent_id in by_id and node.parent_id != node.node_id:
            children[node.parent_id].append(node)
        else:
            roots.append(node)

    roots.sort(key=lambda node: source_order[node.node_id])
    for child_nodes in children.values():
        child_nodes.sort(key=lambda node: source_order[node.node_id])

    options: list[dict[str, str | int]] = []
    actual_roots: list[OrganizationNode] = []
    visited: set[str] = set()

    def walk(node: OrganizationNode, depth: int, root_id: str) -> None:
        if node.node_id in visited:
            return
        visited.add(node.node_id)
        options.append(
            {
                "node_id": node.node_id,
                "code": node.code,
                "name": node.name,
                "full_path": node.full_path,
                "root_id": root_id,
                "depth": depth,
                "label": f"{'— ' * depth}{node.name} ({node.code})",
            }
        )
        for child in children.get(node.node_id, []):
            walk(child, depth + 1, root_id)

    for root in roots:
        actual_roots.append(root)
        walk(root, 0, root.node_id)

    # A malformed or cyclic source must not make a business node disappear.
    for node in nodes:
        if node.node_id not in visited:
            actual_roots.append(node)
            walk(node, 0, node.node_id)

    root_options = [
        {
            "node_id": node.node_id,
            "label": f"{node.full_path} ({node.code})",
        }
        for node in actual_roots
    ]
    return root_options, options


def create_app(runtime_dir: str | Path | None = None) -> FastAPI:
    resolved_runtime = Path(runtime_dir or os.environ.get("EXCEL_TRANSFORM_RUNTIME", "runtime"))
    service = WorkflowService(resolved_runtime)

    # Owner decision: V1 has no organization permission filtering. Clear any
    # legacy local delegation state left by an earlier Draft build.
    service.set_delegations([])

    app = FastAPI(title="Excel → OPIU Light", docs_url=None, redoc_url=None)
    app.state.workflow = service
    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    def page(request: Request, name: str, **context):
        common = {
            "request": request,
            "report_type_name": REPORT_TYPE_NAME,
            "report_type_code": REPORT_TYPE_CODE,
        }
        common.update(context)
        return templates.TemplateResponse(request, name, common)

    @app.get("/")
    def home(request: Request, message: str = "", error: str = ""):
        organization_roots, organization_options = _organization_tree_context(
            service.organization_nodes()
        )
        return page(
            request,
            "home.html",
            counts=service.reference_counts(),
            scenarios=service.store.list_scenarios(),
            organization_roots=organization_roots,
            organization_options=organization_options,
            message=message,
            error=error,
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/references")
    async def upload_reference(
        request: Request,
        kind: str = Form(...),
        reference_file: UploadFile = File(...),
    ):
        try:
            count = service.upload_reference(kind, await reference_file.read())
        except Exception as exc:
            return RedirectResponse(f"/?error={str(exc)}", status_code=303)
        return RedirectResponse(f"/?message=Загружено записей: {count}", status_code=303)

    @app.post("/scenarios")
    def add_scenario(name: str = Form(...), year: int = Form(...), comment: str = Form("")):
        scenario = service.store.add_scenario(name=name, year=year, comment=comment)
        return RedirectResponse(
            f"/?message=Сценарий {scenario.name} сохранён. {scenario.marker}", status_code=303
        )

    @app.post("/uploads")
    async def upload_budget(
        request: Request,
        budget_file: UploadFile = File(...),
        reporting_unit: str = Form(...),
        organization_node_id: str = Form(...),
        scenario_id: str = Form(...),
        year: str = Form(""),
        period_selector_present: str = Form(""),
        all_year: str = Form(""),
        months: list[int] = Form(default=[]),
        workbook_password: str = Form(""),
    ):
        try:
            # Old API/tests without the new marker retain the historical
            # semantics: no month filter means all twelve months.
            all_year_selected = bool(all_year) or not period_selector_present
            if period_selector_present and not all_year_selected and not months:
                raise ValueError("Выберите «Весь год» либо хотя бы один месяц")
            selected_months = [] if all_year_selected else months

            context = service.build_context(
                reporting_unit=reporting_unit,
                organization_node_id=organization_node_id,
                scenario_id=scenario_id,
                year=int(year) if year else None,
                months=selected_months,
            )
            pending = await service.prepare_upload_stream(
                budget_file.filename or "source.xlsx",
                budget_file,
                context,
                password=workbook_password,
            )
        except Exception as exc:
            return home(request, error=str(exc))
        if not pending.candidates:
            return page(request, "blocked.html", pending=pending)
        if len(pending.candidates) > 1:
            return page(request, "choose_candidate.html", pending=pending)
        run = await asyncio.to_thread(
            service.process_upload,
            pending.upload_id,
            pending.candidates[0].candidate_id,
        )
        return RedirectResponse(f"/runs/{run.run_id}", status_code=303)

    @app.post("/uploads/{upload_id}/process")
    async def process_candidate(
        request: Request,
        upload_id: str,
        candidate_id: str = Form(...),
    ):
        try:
            run = await asyncio.to_thread(service.process_upload, upload_id, candidate_id)
        except Exception as exc:
            return home(request, error=str(exc))
        return RedirectResponse(f"/runs/{run.run_id}", status_code=303)

    @app.post("/uploads/{upload_id}/reset")
    def reset_upload(upload_id: str):
        service.reset_upload(upload_id)
        return RedirectResponse("/?message=Выбор файла сброшен", status_code=303)

    @app.get("/runs/{run_id}")
    def preview(request: Request, run_id: str, message: str = "", error: str = ""):
        try:
            run = service.get_run(run_id)
        except KeyError:
            return home(request, error="RUN не найден; выберите файл повторно")
        records = run.visible_records()
        manual_mappings = service.store.load_manual_mappings()
        already_confirmed_rows = {
            record.source_row
            for record in run.records
            if record.erp_code
            and manual_mappings.get(record.mapping_key) == record.erp_code
        }
        bulk_confirmable_rows = [
            source_row
            for source_row in service.bulk_confirmable_source_rows(run_id)
            if source_row not in already_confirmed_rows
        ]
        return page(
            request,
            "run.html",
            run=run,
            records=records,
            unresolved=run.unresolved_issues,
            source_rows=sorted({record.source_row for record in run.records}),
            articles=service.erp_articles(),
            organization_values=sorted({node.full_path for node in service.organization_nodes()}),
            groups=sorted({article.expense_group for article in service.erp_articles()}),
            source_articles=sorted({article.source_article for article in service.erp_articles()}),
            bulk_confirmable_rows=bulk_confirmable_rows,
            message=message,
            error=error,
        )

    @app.post("/runs/{run_id}/correct")
    def correct(
        request: Request,
        run_id: str,
        source_row: int = Form(...),
        erp_code: str = Form(""),
        tax: str = Form(""),
        department: str = Form(""),
        cfo: str = Form(""),
        expense_group: str = Form(""),
        source_article: str = Form(""),
    ):
        try:
            service.correct_row(
                run_id,
                source_row,
                {
                    "erp_code": erp_code,
                    "tax": tax,
                    "department": department,
                    "cfo": cfo,
                    "expense_group": expense_group,
                    "source_article": source_article,
                },
            )
        except Exception as exc:
            return preview(request, run_id, error=str(exc))
        return RedirectResponse(
            f"/runs/{run_id}?message=Исправление применено без повторного запуска",
            status_code=303,
        )

    @app.post("/runs/{run_id}/confirm-filled-erp")
    def confirm_filled_erp(
        request: Request,
        run_id: str,
        confirmed: str = Form(""),
        selections: str = Form("[]"),
    ):
        try:
            if not confirmed:
                raise ValueError("Поставьте галку подтверждения перед массовым применением")
            payload = json.loads(selections)
            if not isinstance(payload, list):
                raise ValueError("Список ERP-сопоставлений заполнен некорректно")
            _, count = service.confirm_filled_erp(run_id, payload)
        except json.JSONDecodeError:
            return preview(
                request,
                run_id,
                error="Список ERP-сопоставлений заполнен некорректно",
            )
        except Exception as exc:
            return preview(request, run_id, error=str(exc))
        return RedirectResponse(
            f"/runs/{run_id}?message=Подтверждено ERP-сопоставлений: {count}. Остальные причины сохранены",
            status_code=303,
        )

    @app.get("/runs/{run_id}/export")
    def export(run_id: str):
        payload = service.export_run(run_id)
        return Response(
            payload,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="opiu-light.xlsx"'},
        )

    return app
