from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from vrenamer.webui.services import pipeline
from vrenamer.webui.settings import Settings


app = FastAPI(title="VideoRenamer WebUI", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request}
    )


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    custom_prompt: str = Form(""),
    n_candidates: int = Form(5),
):
    settings = Settings()  # loads .env

    # Enforce single-video processing
    if file.content_type and not file.content_type.startswith("video/"):
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "只支持单个视频文件"},
            status_code=400,
        )

    with tempfile.TemporaryDirectory(prefix="vren-") as tmpdir:
        tmp_path = Path(tmpdir) / file.filename
        data = await file.read()
        tmp_path.write_bytes(data)

        result = await pipeline.run_single(
            video_path=tmp_path,
            user_prompt=custom_prompt,
            n_candidates=n_candidates,
            settings=settings,
        )

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "result": result,
        },
    )


@app.post("/feedback")
async def feedback(selected_name: str = Form(...), context: str = Form("") ):
    await pipeline.store_feedback(selected_name=selected_name, context=context)
    return RedirectResponse(url="/", status_code=303)

