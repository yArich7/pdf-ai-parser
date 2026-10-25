#!/usr/bin/env python3
"""PDF 智能解析 — FastAPI 后端服务。

启动（在项目根目录）：
    cd backend && uvicorn server:app --host 127.0.0.1 --port 8000

接口契约见 docs/design.md 第 9 章。
"""
import json
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import parse_pdf

BASE_DIR = parse_pdf.BASE_DIR
UPLOAD_DIR = BASE_DIR / "tmp" / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

ALLOWED_FORMATS = {"markdown", "pdf", "docx", "html"}
ALLOWED_DOC_TYPES = {"drawing", "spec", "report", "bom", "contract", "manual", "generic"}

app = FastAPI(title="PDF 智能解析")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS = {}
_lock = threading.Lock()


def _err(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "index.html")


@app.post("/v1/parse", status_code=202)
async def submit_parse(
    file: UploadFile = File(...),
    options: str = Form("{}"),
    x_api_key: str = Header(default=None, alias="X-API-Key"),
):
    try:
        opts = json.loads(options) if options else {}
    except json.JSONDecodeError:
        return _err(400, "invalid_options", "options 不是合法 JSON")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return _err(400, "invalid_file_type", "仅支持 PDF 文件")

    fmt = opts.get("format", "markdown")
    if fmt not in ALLOWED_FORMATS:
        return _err(400, "invalid_options", f"format 取值非法: {fmt}")
    doc_type = opts.get("doc_type")
    if doc_type in ("auto", "", None):
        doc_type = None
    elif doc_type not in ALLOWED_DOC_TYPES:
        return _err(400, "invalid_options", f"doc_type 取值非法: {doc_type}")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        return _err(400, "file_too_large", "文件超过 50 MB")

    job_id = "job_" + uuid.uuid4().hex[:12]
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"
    pdf_path.write_bytes(content)

    job = {
        "job_id": job_id,
        "original_name": file.filename,
        "api_key": (x_api_key or "").strip() or None,
        "status": "queued",
        "stage": "排队中",
        "doc_type": None,
        "confidence": None,
        "pages": None,
        "report": None,
        "format": fmt,
        "output_path": None,
        "error": None,
        "created_at": time.time(),
    }
    with _lock:
        JOBS[job_id] = job
    threading.Thread(target=_run, args=(job_id, pdf_path), daemon=True).start()
    return {"job_id": job_id, "status": "queued"}


def _run(job_id: str, pdf_path: Path):
    job = JOBS[job_id]
    try:
        parse_pdf._api_key_ctx.set(job.get("api_key") or "")

        def cb(msg):
            with _lock:
                job["stage"] = msg
                job["status"] = "running"

        result = parse_pdf.parse_document(
            pdf_path, progress_cb=cb, source_name=job["original_name"]
        )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / f"{job_id}_报告.md"
        out.write_text(result["report"], encoding="utf-8")

        with _lock:
            job.update({
                "status": "success",
                "stage": "完成",
                "doc_type": result["doc_type"],
                "confidence": result["confidence"],
                "pages": result["pages"],
                "report": result["report"],
                "output_path": str(out),
            })
    except Exception as e:
        with _lock:
            job.update({
                "status": "failed",
                "stage": "失败",
                "error": {"code": "parse_failed", "message": str(e)},
            })


@app.get("/v1/parse/{job_id}")
def get_job(job_id: str):
    with _lock:
        job = JOBS.get(job_id)
        if not job:
            return _err(404, "job_not_found", "任务不存在")
        if job["status"] == "success":
            return {
                "job_id": job_id,
                "status": "success",
                "doc_type": job["doc_type"],
                "confidence": job["confidence"],
                "pages": job["pages"],
                "report": job["report"],
                "format": job["format"],
                "download_url": None,
            }
        if job["status"] == "failed":
            return {"job_id": job_id, "status": "failed", "error": job["error"]}
        return {"job_id": job_id, "status": job["status"], "stage": job["stage"]}


@app.get("/v1/parse/{job_id}/download")
def download(job_id: str, format: str = "markdown"):
    with _lock:
        job = JOBS.get(job_id)
    if not job:
        return _err(404, "job_not_found", "任务不存在")
    if job["status"] != "success":
        return _err(409, "not_ready", "任务尚未完成")
    if format != "markdown":
        return _err(501, "not_supported", "暂仅支持 markdown 下载")
    path = Path(job["output_path"])
    if not path.exists():
        return _err(404, "file_missing", "报告文件不存在")
    return FileResponse(path, filename=path.name, media_type="text/markdown")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
