from flask import Blueprint, render_template, jsonify, request
from models import alert
from utils.helpers import clean

bp = Blueprint("alerts", __name__)

@bp.route("/alerts")
def page():
    return render_template("alerts.html")

@bp.route("/api/alerts")
def api():
    rows = alert.list_alerts(request.args.get("severity", "medium"), request.args.get("status") or None,
                             request.args.get("campaign_id", type=int), request.args.get("days", type=int),
                             request.args.get("limit", 200, type=int))
    return jsonify(clean(rows))

@bp.route("/api/alerts/<int:aid>/status", methods=["POST"])
def status(aid):
    alert.set_status(aid, "acknowledged" if (request.json or {}).get("status") == "acknowledged" else "open")
    return jsonify(ok=True)
