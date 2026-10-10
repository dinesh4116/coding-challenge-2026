from flask import Blueprint, render_template, jsonify, abort
from models import campaign, metric, alert
from utils.helpers import clean

bp = Blueprint("campaigns", __name__)

@bp.route("/campaigns")
def campaigns():
    return render_template("campaigns.html", campaigns=campaign.all_with_stats())

@bp.route("/campaigns/<int:cid>")
def details(cid):
    c = campaign.get(cid) or abort(404)
    return render_template("campaign_details.html", c=c)

@bp.route("/api/campaigns/<int:cid>/series")
def series(cid):
    return jsonify(clean({"series": metric.series(cid),
                          "alerts": alert.list_alerts("low", cid=cid, limit=500)}))
