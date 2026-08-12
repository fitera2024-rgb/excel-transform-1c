from __future__ import annotations

import uvicorn

from excel_transform_1c.ui.app import create_app

app = create_app()


def run() -> None:
    uvicorn.run("excel_transform_1c.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
