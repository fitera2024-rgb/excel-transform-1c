from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from excel_transform_1c.application.service import WorkflowService
from excel_transform_1c.core.models import REPORT_TYPE_CODE, REPORT_TYPE_NAME


PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(runtime_dir: str | Path | None = None) -> FastAPI:
    resolved_runtime = Path(runtime_dir or os.environ.get("EXCEL_TRANSFORM_RUNTIME", "runtime"))
    service = WorkflowService(resolved_runtime)
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
        return page(
            request,
            "home.html",
            counts=service.reference_counts(),
            scenarios=service.store.list_scenarios(),
            organizations=service.allowed_organization_nodes(),
            all_organizations=service.organization_nodes(),
            delegations=set(service.store.get_delegations("local")),
            message=message,
            error=error,
        )

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

    @app.post("/delegations")
    def set_delegations(node_ids: list[str] = Form(default=[])):
        service.set_delegations(node_ids)
        return RedirectResponse("/?message=Область доступа обновлена", status_code=303)

    @app.post("/uploads")
    async def upload_budget(
        request: Request,
        budget_file: UploadFile = File(...),
        reporting_unit: str = Form(...),
        organization_node_id: str = Form(...),
        scenario_id: str = Form(...),
        year: str = Form(""),
        months: list[int] = Form(default=[]),
    ):
        try:
            context = service.build_context(
                reporting_unit=reporting_unit,
                organization_node_id=organization_node_id,
                scenario_id=scenario_id,
                year=int(year) if year else None,
                months=months,
            )
            pending = service.prepare_upload(budget_file.filename or "source.xlsx", await budget_file.read(), context)
        except Exception as exc:
            return home(request, error=str(exc))
        if not pending.candidates:
            return page(request, "blocked.html", pending=pending)
        if len(pending.candidates) > 1:
            return page(request, "choose_candidate.html", pending=pending)
        run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
        return RedirectResponse(f"/runs/{run.run_id}", status_code=303)

    @app.post("/uploads/{upload_id}/process")
    def process_candidate(request: Request, upload_id: str, candidate_id: str = Form(...)):
        try:
            run = service.process_upload(upload_id, candidate_id)
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
        return RedirectResponse(f"/runs/{run_id}?message=Исправление применено без повторного запуска", status_code=303)

    @app.get("/runs/{run_id}/export")
    def export(run_id: str):
        payload = service.export_run(run_id)
        return Response(
            payload,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="opiu-light.xlsx"'},
        )

    return app
