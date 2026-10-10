from flask import Blueprint, render_template, jsonify
from models import alert
from utils.helpers import clean

bp = Blueprint("dashboard", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@bp.route("/api/summary")
def summary():
    return jsonify(clean(alert.summary()))
