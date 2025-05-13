from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required
from reports.ar_service import fetch_ar_aging_report

ar_bp = Blueprint("ar_reporting", __name__, template_folder="templates")

@ar_bp.route("/")
@login_required
def ar_reporting():
    # Optional URL‑param: multiple ?channel=Faire
    channels = request.args.getlist("channel") or None

    # Get our 3×6 summary
    df = fetch_ar_aging_report(
        as_of=date.today(),
        channels=channels,
        debug=False
    )
    rows = df.to_dict(orient="records")
    today = date.today().strftime("%Y-%m-%d")

    return render_template(
        "ar_reporting.html",
        rows=rows,
        today=today
    )
