from __future__ import annotations

import asyncio
import hashlib
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
    TAX_NOT_REQUIRED,
)


PACKAGE_DIR = Path(__file__).resolve().parent


def _static_version() -> str:
    digest = hashlib.sha256()
    for file_name in ("app.css", "run.js"):
        digest.update((PACKAGE_DIR / "static" / file_name).read_bytes())
    return digest.hexdigest()[:12]


STATIC_VERSION = _static_version()


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

    @app.middleware("http")
    async def prevent_stale_local_ui(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/static/", "/runs/")):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

    def page(request: Request, name: str, **context):
        common = {
            "request": request,
            "report_type_name": REPORT_TYPE_NAME,
            "report_type_code": REPORT_TYPE_CODE,
            "static_version": STATIC_VERSION,
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
        confirmed_erp_rows = service.confirmed_erp_source_rows(run_id)
        bulk_confirmable_rows = [
            source_row
            for source_row in service.bulk_confirmable_source_rows(run_id)
            if source_row not in confirmed_erp_rows
        ]
        _, organization_options = _organization_tree_context(service.organization_nodes())
        return page(
            request,
            "run.html",
            run=run,
            records=records,
            unresolved=run.unresolved_issues,
            source_rows=sorted({record.source_row for record in run.records}),
            articles=service.erp_articles(),
            organization_values=sorted({node.full_path for node in service.organization_nodes()}),
            organization_options=organization_options,
            groups=sorted({article.expense_group for article in service.erp_articles()}),
            source_articles=sorted({article.source_article for article in service.erp_articles()}),
            bulk_confirmable_rows=bulk_confirmable_rows,
            confirmed_erp_rows=confirmed_erp_rows,
            tax_not_required_rows=service.tax_not_required_source_rows(run_id),
            cfo_mapping_entries=service.cfo_mapping_entries(run_id),
            indicator_counts=service.indicator_counts(run_id),
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
        tax_not_required: str = Form(""),
    ):
        try:
            selected_tax = TAX_NOT_REQUIRED if tax_not_required else tax
            service.correct_row(
                run_id,
                source_row,
                {
                    "erp_code": erp_code,
                    "tax": selected_tax,
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

    @app.post("/runs/{run_id}/confirm-tax-not-required")
    def confirm_tax_not_required(
        request: Request,
        run_id: str,
        confirmed: str = Form(""),
        source_rows: str = Form("[]"),
    ):
        try:
            if not confirmed:
                raise ValueError("Поставьте галку подтверждения перед массовым применением")
            payload = json.loads(source_rows)
            if not isinstance(payload, list):
                raise ValueError("Список строк по налогообложению заполнен некорректно")
            _, count = service.confirm_tax_not_required(run_id, payload)
        except json.JSONDecodeError:
            return preview(
                request,
                run_id,
                error="Список строк по налогообложению заполнен некорректно",
            )
        except Exception as exc:
            return preview(request, run_id, error=str(exc))
        return RedirectResponse(
            f"/runs/{run_id}?message=Налогообложение отмечено как не требующееся: "
            f"{count} строк. Остальные причины сохранены",
            status_code=303,
        )

    @app.post("/runs/{run_id}/map-cfo")
    def map_cfo(
        request: Request,
        run_id: str,
        single_source_key: str = Form(""),
        source_key: str = Form(""),
        target_node_id: str = Form(""),
        source_keys: list[str] = Form(default=[]),
        target_node_ids: list[str] = Form(default=[]),
        confirmed_source_keys: list[str] = Form(default=[]),
        confirmed: str = Form(""),
    ):
        try:
            selected_source_key = single_source_key or source_key
            selected_target_node_id = target_node_id
            if single_source_key:
                if len(source_keys) != len(target_node_ids):
                    raise ValueError("Список сопоставлений ЦФО заполнен некорректно")
                by_source_key = dict(zip(source_keys, target_node_ids, strict=True))
                selected_target_node_id = by_source_key.get(single_source_key, "")
                confirmed = "1" if single_source_key in set(confirmed_source_keys) else ""
            if not confirmed:
                raise ValueError("Поставьте галку «Подтверждаю соответствие ЦФО»")
            if not selected_source_key or not selected_target_node_id:
                raise ValueError("Выберите точный узел 1С для ЦФО")
            _, count = service.confirm_cfo_mappings(
                run_id,
                [
                    {
                        "source_key": selected_source_key,
                        "target_node_id": selected_target_node_id,
                    }
                ],
            )
        except Exception as exc:
            return preview(request, run_id, error=str(exc))
        return RedirectResponse(
            f"/runs/{run_id}?message=Сопоставление ЦФО подтверждено. "
            f"Обновлено новых соответствий: {count}",
            status_code=303,
        )

    @app.post("/runs/{run_id}/confirm-filled-cfo")
    def confirm_filled_cfo(
        request: Request,
        run_id: str,
        confirmed: str = Form(""),
        selections: str = Form("[]"),
        source_keys: list[str] = Form(default=[]),
        target_node_ids: list[str] = Form(default=[]),
    ):
        try:
            if not confirmed:
                raise ValueError("Поставьте галку подтверждения перед массовым применением")
            if source_keys or target_node_ids:
                if len(source_keys) != len(target_node_ids):
                    raise ValueError("Список сопоставлений ЦФО заполнен некорректно")
                payload = [
                    {"source_key": key, "target_node_id": target}
                    for key, target in zip(source_keys, target_node_ids, strict=True)
                    if key and target
                ]
            else:
                payload = json.loads(selections)
            if not isinstance(payload, list):
                raise ValueError("Список сопоставлений ЦФО заполнен некорректно")
            _, count = service.confirm_cfo_mappings(run_id, payload)
        except json.JSONDecodeError:
            return preview(
                request,
                run_id,
                error="Список сопоставлений ЦФО заполнен некорректно",
            )
        except Exception as exc:
            return preview(request, run_id, error=str(exc))
        return RedirectResponse(
            f"/runs/{run_id}?message=Подтверждено новых сопоставлений ЦФО: "
            f"{count}. Остальные причины сохранены",
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

    @app.post("/runs/{run_id}/indicator-classifier")
    async def upload_indicator_classifier(
        request: Request,
        run_id: str,
        classifier_file: UploadFile = File(...),
    ):
        try:
            count = service.upload_indicator_classifier(
                await classifier_file.read(),
                run_id,
            )
        except KeyError:
            return home(request, error="RUN не найден; выберите файл повторно")
        except Exception as exc:
            return preview(request, run_id, error=str(exc))
        return RedirectResponse(
            f"/runs/{run_id}?message=Классификатор дополнен: {count}. "
            "Автоматический поиск повторён в текущем RUN",
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
