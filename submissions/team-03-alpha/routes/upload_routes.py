from flask import Blueprint, render_template, request, flash, redirect, url_for
from config import Config
from services.data_processor import process

bp = Blueprint("upload", __name__)

@bp.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        try:
            f = request.files.get("file")
            src = f if f and f.filename else Config.SAMPLE_CSV
            r = process(src)
            flash(f"Processed {r['rows']} rows across {r['campaigns']} campaigns - {r['alerts']} alerts detected.", "ok")
            return redirect(url_for("dashboard.dashboard"))
        except Exception as e:
            flash(f"Upload failed: {e}", "err")
    return render_template("upload.html")
