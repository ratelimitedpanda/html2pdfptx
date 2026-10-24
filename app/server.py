import io
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from urllib.parse import quote

from flask import Flask, abort, jsonify, render_template, request, send_file, send_from_directory

from .build_pdf import build_pdf
from .build_pptx import build_presentation
from .capture import capture_slides
from .unpack import unpack_upload

sys.stdout.reconfigure(encoding="utf-8")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

WORK_DIR = tempfile.mkdtemp(prefix="html2deck-")
JOB_LIFETIME = 60 * 60
MODES = ("auto", "keyboard", "scroll")
KEYS = ("ArrowRight", "ArrowDown", "PageDown", "Space", "click")

jobs = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/render/<job_id>/<path:filename>")
def render(job_id, filename):
    if job_id not in jobs:
        abort(404)
    return send_from_directory(jobs[job_id]["dir"], filename)


@app.route("/convert", methods=["POST"])
def convert():
    _remove_old_jobs()
    file = request.files["document"]

    job_id = uuid.uuid4().hex
    job_dir = os.path.join(WORK_DIR, job_id)
    os.makedirs(job_dir)

    try:
        entry = unpack_upload(file, job_dir)
    except ValueError as error:
        shutil.rmtree(job_dir, ignore_errors=True)
        return str(error), 400

    job = {
        "dir": job_dir,
        "name": os.path.splitext(file.filename)[0] or "presentation",
        "status": "running",
        "message": "Открываю презентацию...",
        "mode": None,
        "slides": [],
        "total": None,
        "created": time.time(),
    }
    jobs[job_id] = job

    settings = _read_settings(request.form)
    settings["on_mode"] = lambda mode: job.update(mode=mode)
    settings["on_progress"] = lambda slides, total: job.update(slides=slides, total=total)

    url = f"{request.host_url}render/{job_id}/{quote(entry)}"
    threading.Thread(target=_run_job, args=(job, url, settings), daemon=True).start()
    print(f"Открываю {file.filename}")

    return jsonify(id=job_id)


@app.route("/jobs/<job_id>")
def job_status(job_id):
    job = _get_job(job_id)
    return jsonify(
        status=job["status"],
        message=job["message"],
        mode=job["mode"],
        count=len(job["slides"]),
        total=job["total"],
        scale=job.get("scale", 1),
    )


@app.route("/jobs/<job_id>/slides/<int:number>.png")
def slide_image(job_id, number):
    slides = _get_job(job_id)["slides"]
    if not 0 <= number < len(slides):
        abort(404)
    response = send_file(io.BytesIO(slides[number]["png"]), mimetype="image/png")
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@app.route("/jobs/<job_id>/download")
def download(job_id):
    job = _get_job(job_id)
    if job["status"] != "done":
        return "Слайды ещё не сняты", 409

    output_format = "pptx" if request.args.get("format") == "pptx" else "pdf"
    slides = _pick_slides(job["slides"], request.args.get("slides"))
    if not slides:
        return "Не выбрано ни одного слайда", 400

    output_path = os.path.join(job["dir"], f"result.{output_format}")
    if output_format == "pdf":
        build_pdf(slides, output_path, scale=job["scale"])
    else:
        build_presentation(slides, output_path)

    return send_file(output_path, as_attachment=True, download_name=f"{job['name']}.{output_format}")


def _run_job(job, url, settings):
    job["scale"] = settings["scale"]
    job["message"] = "Снимаю слайды..."
    try:
        mode, slides = capture_slides(url, settings)
        job.update(mode=mode, slides=slides, status="done", message=f"Готово: {len(slides)} слайдов, режим {mode}")
    except Exception as error:
        job.update(status="error", message=f"Не удалось снять слайды: {error}")
    print(job["message"])


def _read_settings(form):
    width, height = (_to_int(v, 0) for v in form.get("size", "1280x720").split("x"))
    return {
        "mode": form.get("mode") if form.get("mode") in MODES else "auto",
        "width": _clamp(width or 1280, 320, 3840),
        "height": _clamp(height or 720, 240, 2160),
        "scale": _clamp(_to_int(form.get("scale"), 2), 1, 3),
        "fragments": "steps" if form.get("fragments") == "steps" else "final",
        "key": form.get("key") if form.get("key") in KEYS else "ArrowRight",
        "settle_ms": _clamp(_to_int(form.get("pause"), 400), 0, 10000),
        "max_slides": _clamp(_to_int(form.get("max_slides"), 300), 1, 1000),
        "hide_controls": form.get("hide_controls") == "on",
        "freeze_animations": form.get("freeze") == "on",
    }


def _pick_slides(slides, numbers_text):
    if not numbers_text:
        return slides
    numbers = [_to_int(n, -1) for n in numbers_text.split(",")]
    return [slides[n] for n in numbers if 0 <= n < len(slides)]


def _get_job(job_id):
    if job_id not in jobs:
        abort(404)
    return jobs[job_id]


def _remove_old_jobs():
    for job_id, job in list(jobs.items()):
        if job["status"] != "running" and time.time() - job["created"] > JOB_LIFETIME:
            shutil.rmtree(job["dir"], ignore_errors=True)
            del jobs[job_id]


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, low, high):
    return max(low, min(high, value))
