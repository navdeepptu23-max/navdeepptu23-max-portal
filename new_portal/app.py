import os
import secrets
import csv
import io
import json
from functools import wraps
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///portal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship("HospitalReport", backref="owner", lazy=True, cascade="all, delete-orphan")
    morbidity_reports = db.relationship("MorbidityReport", backref="morbidity_owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class HospitalReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    hospital_name = db.Column(db.String(255), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    month_year = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notes = db.Column(db.Text, default="")

    # OUTPATIENTS — New
    op_new_male = db.Column(db.Integer, default=0)
    op_new_female = db.Column(db.Integer, default=0)
    op_new_male_child = db.Column(db.Integer, default=0)
    op_new_female_child = db.Column(db.Integer, default=0)
    # OUTPATIENTS — Old
    op_old_male = db.Column(db.Integer, default=0)
    op_old_female = db.Column(db.Integer, default=0)
    op_old_male_child = db.Column(db.Integer, default=0)
    op_old_female_child = db.Column(db.Integer, default=0)
    # OUTPATIENTS — Emergency
    op_emer_male = db.Column(db.Integer, default=0)
    op_emer_female = db.Column(db.Integer, default=0)
    op_emer_male_child = db.Column(db.Integer, default=0)
    op_emer_female_child = db.Column(db.Integer, default=0)

    # Admissions during the month
    adm_male = db.Column(db.Integer, default=0)
    adm_female = db.Column(db.Integer, default=0)
    adm_male_child = db.Column(db.Integer, default=0)
    adm_female_child = db.Column(db.Integer, default=0)
    # Admissions through emergency
    adm_emer_male = db.Column(db.Integer, default=0)
    adm_emer_female = db.Column(db.Integer, default=0)
    adm_emer_male_child = db.Column(db.Integer, default=0)
    adm_emer_female_child = db.Column(db.Integer, default=0)
    # Medical legal cases admitted
    mlc_male = db.Column(db.Integer, default=0)
    mlc_female = db.Column(db.Integer, default=0)
    mlc_male_child = db.Column(db.Integer, default=0)
    mlc_female_child = db.Column(db.Integer, default=0)
    # Admitted & discharged same day
    sdd_male = db.Column(db.Integer, default=0)
    sdd_female = db.Column(db.Integer, default=0)
    sdd_male_child = db.Column(db.Integer, default=0)
    sdd_female_child = db.Column(db.Integer, default=0)

    # Tubectomies (incl. laparoscopic)
    tubec_male = db.Column(db.Integer, default=0)
    tubec_female = db.Column(db.Integer, default=0)
    tubec_male_child = db.Column(db.Integer, default=0)
    tubec_female_child = db.Column(db.Integer, default=0)
    # Vasectomies
    vasec_male = db.Column(db.Integer, default=0)
    vasec_female = db.Column(db.Integer, default=0)
    vasec_male_child = db.Column(db.Integer, default=0)
    vasec_female_child = db.Column(db.Integer, default=0)
    # Minor surgeries (exc. vasectomies)
    minor_surg_male = db.Column(db.Integer, default=0)
    minor_surg_female = db.Column(db.Integer, default=0)
    minor_surg_male_child = db.Column(db.Integer, default=0)
    minor_surg_female_child = db.Column(db.Integer, default=0)
    # Major surgeries (exc. tubectomies)
    major_surg_male = db.Column(db.Integer, default=0)
    major_surg_female = db.Column(db.Integer, default=0)
    major_surg_male_child = db.Column(db.Integer, default=0)
    major_surg_female_child = db.Column(db.Integer, default=0)

    # Deaths
    deaths_male = db.Column(db.Integer, default=0)
    deaths_female = db.Column(db.Integer, default=0)
    deaths_male_child = db.Column(db.Integer, default=0)
    deaths_female_child = db.Column(db.Integer, default=0)

    # Deliveries (single values — not split by gender)
    normal_deliveries = db.Column(db.Integer, default=0)
    caesarean_deliveries = db.Column(db.Integer, default=0)
    # Children born (excluding stillbirth, referenced from deliveries)
    male_children = db.Column(db.Integer, default=0)
    female_children = db.Column(db.Integer, default=0)

    # Aggregate / other stats
    lab_tests = db.Column(db.Integer, default=0)
    cumulative_inpatient_days = db.Column(db.Integer, default=0)
    user_charges_collection = db.Column(db.Integer, default=0)
    rsby_cases = db.Column(db.Integer, default=0)


MORBIDITY_DISEASES = [
    ("2", "Typhoid Fever and Paratyphoid Fever"),
    ("5", "Amoebiasis"),
    ("6", "Diarrhoea"),
    ("8", "Respiratory TB"),
    ("10", "T.B of other organ"),
    ("29", "Measles"),
    ("31", "Other Viral Hepatitis"),
    ("32", "HIV"),
    ("37", "Helminthiasis"),
    ("79", "Other Anaemia"),
    ("85", "Disorders of thyroid glands"),
    ("86", "Diabetes Mellitus"),
    ("89", "Mental and behavioural Disorder"),
    ("98", "Diseases of eye"),
    ("99", "Diseases of the ear"),
    ("102", "Hypertensive Heart Disease"),
    ("103", "All other hypertensive diseases"),
    ("114", "Pharyngitis & Tonsillitis"),
    ("116", "Other Acute Upper Respiratory Infections"),
    ("118", "Acute Bronchitis"),
    ("119", "Ch. Bronchitis and unspecified Emphysema"),
    ("120", "Asthma"),
    ("121", "Other lower respiratory disorders"),
    ("126", "Diseases of Oral Cavity"),
    ("127", "Gastric and Duodenal ulcer"),
    ("128", "Gastritis & Duodenitis"),
    ("134", "Cholelithiasis and Cholecystitis"),
    ("136", "Other Diseases other part of Digestive system"),
    ("137", "Infections of skin"),
    ("138", "All other disease of Skin"),
    ("139", "Rheumatoid Arthritis & other inflammatory Polyarthropathies"),
    ("147", "Other diseases of Urinary Track"),
    ("149", "All other Diseases of male genital organs"),
    ("151", "All other diseases of female genital organs"),
    ("152", "Spontaneous Abortion"),
    ("155", "Oedema/ Proteinuria & Hypertension Disorder in Pregnancy/childbirth & puerperium"),
    ("157", "Obstructed Labour"),
    ("158", "Complication predominantly related to puerperium"),
    ("161", "All other obstetric conditions not elsewhere classified"),
    ("172", "Abdominal and Pelvic pain"),
    ("175", "Fever of Unknown origin (PUO)"),
    ("180", "All other Symptoms, Signs & abnormal clinical / lab findings not elsewhere classified"),
    ("186", "Dislocations, sprains & Stains of body regions"),
    ("189", "Other injuries"),
    ("191", "Burns & Corrosions"),
    ("192", "Poisoning by drugs & Biological substances and toxic effect of substances"),
    ("193", "Other specified effects of external causes & certain early complications of trauma"),
    ("198", "Other Road Side Accidents (RSA)"),
    ("215", "Bites of snake & other Venomous animals / DOG BITE"),
]


class MorbidityReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    health_institution_name = db.Column(db.String(255), nullable=False)
    month_year = db.Column(db.String(20), nullable=False)
    entries_json = db.Column(db.Text, default="{}")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


def build_morbidity_payload(form_source):
    payload = {}
    for sr_no, _ in MORBIDITY_DISEASES:
        opd = form_source.get(f"morbidity_{sr_no}_opd", 0, type=int)
        ipd = form_source.get(f"morbidity_{sr_no}_ipd", 0, type=int)
        payload[sr_no] = {"opd": opd, "ipd": ipd}
    return payload


def morbidity_rows(report):
    data = json.loads(report.entries_json or "{}")
    rows = []
    total_opd = 0
    total_ipd = 0

    for sr_no, disease_name in MORBIDITY_DISEASES:
        values = data.get(sr_no, {})
        opd = int(values.get("opd", 0) or 0)
        ipd = int(values.get("ipd", 0) or 0)
        rows.append({
            "sr_no": sr_no,
            "disease_name": disease_name,
            "opd": opd,
            "ipd": ipd,
        })
        total_opd += opd
        total_ipd += ipd

    return rows, total_opd, total_ipd


def total_hospital_outpatients(report):
    return (
        (report.op_new_male or 0) + (report.op_new_female or 0) + (report.op_new_male_child or 0) + (report.op_new_female_child or 0)
        + (report.op_old_male or 0) + (report.op_old_female or 0) + (report.op_old_male_child or 0) + (report.op_old_female_child or 0)
        + (report.op_emer_male or 0) + (report.op_emer_female or 0) + (report.op_emer_male_child or 0) + (report.op_emer_female_child or 0)
    )


def total_hospital_admissions(report):
    return (report.adm_male or 0) + (report.adm_female or 0) + (report.adm_male_child or 0) + (report.adm_female_child or 0)


def create_morbidity_excel(report, rows, total_opd, total_ipd):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Morbidity Report"

    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    header_fill = PatternFill("solid", fgColor="D9D9D9")
    title_font = Font(bold=True, size=12)
    bold_font = Font(bold=True)

    sheet.merge_cells("A1:D1")
    sheet["A1"] = "PROFORMA II"
    sheet["A1"].font = title_font
    sheet["A1"].alignment = Alignment(horizontal="center")

    sheet.merge_cells("A2:D2")
    sheet["A2"] = "MORBIDITY AND MORTALITY REPORT"
    sheet["A2"].font = title_font
    sheet["A2"].alignment = Alignment(horizontal="center")

    sheet["A3"] = f"Name of the Health Institution: {report.health_institution_name}"
    sheet["C3"] = f"Month & Year: {report.month_year}"
    sheet["A3"].font = bold_font
    sheet["C3"].font = bold_font

    headers = ["Sr. No.", "Name of the disease", "OPD", "IPD"]
    for column, value in enumerate(headers, start=1):
        cell = sheet.cell(row=4, column=column, value=value)
        cell.font = bold_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_index = 5
    for row in rows:
        values = [row["sr_no"], row["disease_name"], row["opd"], row["ipd"]]
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row=row_index, column=column, value=value)
            cell.border = border
            cell.alignment = Alignment(horizontal="left" if column == 2 else "center", vertical="center", wrap_text=True)
        row_index += 1

    total_values = ["", "Total", total_opd, total_ipd]
    for column, value in enumerate(total_values, start=1):
        cell = sheet.cell(row=row_index, column=column, value=value)
        cell.font = bold_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    sheet.column_dimensions["A"].width = 10
    sheet.column_dimensions["B"].width = 58
    sheet.column_dimensions["C"].width = 14
    sheet.column_dimensions["D"].width = 14

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def build_consolidated_rows(hospital_reports, morbidity_reports, include_owner=False):
    rows = []

    for report in hospital_reports:
        row = {
            "report_type": "HP Indicator",
            "institution": report.hospital_name,
            "district": report.district,
            "month_year": report.month_year,
            "metric_one_label": "Outpatients",
            "metric_one": total_hospital_outpatients(report),
            "metric_two_label": "Admissions",
            "metric_two": total_hospital_admissions(report),
            "created_at": report.created_at,
            "view_url": url_for("hospital_report_view", report_id=report.id),
        }
        if include_owner:
            row["owner_username"] = report.owner.username
            row["owner_email"] = report.owner.email
            row["view_url"] = url_for("admin_report_view", report_id=report.id)
        rows.append(row)

    for report in morbidity_reports:
        _, total_opd, total_ipd = morbidity_rows(report)
        row = {
            "report_type": "Morbidity",
            "institution": report.health_institution_name,
            "district": "-",
            "month_year": report.month_year,
            "metric_one_label": "OPD",
            "metric_one": total_opd,
            "metric_two_label": "IPD",
            "metric_two": total_ipd,
            "created_at": report.created_at,
            "view_url": url_for("morbidity_report_view", report_id=report.id),
        }
        if include_owner:
            row["owner_username"] = report.morbidity_owner.username
            row["owner_email"] = report.morbidity_owner.email
            row["view_url"] = url_for("admin_morbidity_report_view", report_id=report.id)
        rows.append(row)

    rows.sort(key=lambda item: item["created_at"], reverse=True)
    return rows


def build_consolidated_excel(title, rows, include_owner=False):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Consolidated Report"

    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    header_fill = PatternFill("solid", fgColor="C2410C")
    header_font = Font(bold=True, color="FFFFFF")
    bold_font = Font(bold=True)

    headers = ["Report Type", "Institution", "District", "Month / Year", "Metric 1", "Value 1", "Metric 2", "Value 2", "Created"]
    if include_owner:
        headers.extend(["Owner Username", "Owner Email"])

    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    title_cell = sheet.cell(row=1, column=1, value=title)
    title_cell.font = Font(bold=True, size=13)
    title_cell.alignment = Alignment(horizontal="center")

    for index, value in enumerate(headers, start=1):
        cell = sheet.cell(row=2, column=index, value=value)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_index = 3
    for row in rows:
        values = [
            row["report_type"],
            row["institution"],
            row["district"],
            row["month_year"],
            row["metric_one_label"],
            row["metric_one"],
            row["metric_two_label"],
            row["metric_two"],
            row["created_at"].strftime("%Y-%m-%d"),
        ]
        if include_owner:
            values.extend([row["owner_username"], row["owner_email"]])

        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row=row_index, column=column, value=value)
            cell.border = border
            cell.alignment = Alignment(horizontal="center" if column != 2 else "left", vertical="center", wrap_text=True)
        row_index += 1

    for column_index, width in enumerate([18, 30, 18, 16, 14, 12, 14, 12, 14, 18, 26], start=1):
        if column_index <= len(headers):
            sheet.column_dimensions[chr(64 + column_index)].width = width

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        user = User.query.get(session["user_id"])
        if not user or not user.is_active:
            session.pop("user_id", None)
            flash("Your account is inactive. Contact admin.", "danger")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "admin_id" not in session:
            flash("Admin login required.", "warning")
            return redirect(url_for("admin_login"))
        admin = User.query.get(session["admin_id"])
        if not admin or not admin.is_admin or not admin.is_active:
            session.pop("admin_id", None)
            flash("Unauthorized admin access.", "danger")
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)

    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return None
    return user


def current_admin():
    admin_id = session.get("admin_id")
    if not admin_id:
        return None
    admin = User.query.get(admin_id)
    if admin and admin.is_admin and admin.is_active:
        return admin
    return None


@app.route("/")
def index():
    return render_template("index.html", user=current_user())


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([username, email, password]):
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account is inactive. Contact admin.", "danger")
                return redirect(url_for("login"))
            session["user_id"] = user.id
            flash(f"Welcome back, {user.username}.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html", user=current_user())


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([username, email, new_password, confirm_password]):
            flash("All fields are required.", "danger")
            return redirect(url_for("forgot_password"))

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("forgot_password"))

        if len(new_password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("forgot_password"))

        user = User.query.filter_by(username=username, email=email).first()
        if not user:
            flash("No account matched that username and email.", "danger")
            return redirect(url_for("forgot_password"))

        user.set_password(new_password)
        db.session.commit()
        flash("Password updated successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html", user=current_user())


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    reports = HospitalReport.query.filter_by(user_id=user.id).order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports = MorbidityReport.query.filter_by(user_id=user.id).order_by(MorbidityReport.created_at.desc()).all()
    morbidity_summaries = []
    for report in morbidity_reports[:5]:
        _, total_opd, total_ipd = morbidity_rows(report)
        morbidity_summaries.append({
            "report": report,
            "total_opd": total_opd,
            "total_ipd": total_ipd,
        })

    return render_template(
        "dashboard.html",
        user=user,
        reports=reports,
        morbidity_reports=morbidity_reports,
        morbidity_summaries=morbidity_summaries,
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


@app.route("/hospital/report/new", methods=["GET", "POST"])
@login_required
def new_hospital_report():
    user = current_user()
    if request.method == "POST":
        hospital_name = request.form.get("hospital_name", "").strip()
        district = request.form.get("district", "").strip()
        month_year = request.form.get("month_year", "").strip()

        if not all([hospital_name, district, month_year]):
            flash("Hospital name, district, and month/year are required.", "danger")
            return redirect(url_for("new_hospital_report"))

        def fi(name):
            return request.form.get(name, 0, type=int)

        report = HospitalReport(
            user_id=user.id,
            hospital_name=hospital_name,
            district=district,
            month_year=month_year,
            op_new_male=fi("op_new_male"), op_new_female=fi("op_new_female"),
            op_new_male_child=fi("op_new_male_child"), op_new_female_child=fi("op_new_female_child"),
            op_old_male=fi("op_old_male"), op_old_female=fi("op_old_female"),
            op_old_male_child=fi("op_old_male_child"), op_old_female_child=fi("op_old_female_child"),
            op_emer_male=fi("op_emer_male"), op_emer_female=fi("op_emer_female"),
            op_emer_male_child=fi("op_emer_male_child"), op_emer_female_child=fi("op_emer_female_child"),
            adm_male=fi("adm_male"), adm_female=fi("adm_female"),
            adm_male_child=fi("adm_male_child"), adm_female_child=fi("adm_female_child"),
            adm_emer_male=fi("adm_emer_male"), adm_emer_female=fi("adm_emer_female"),
            adm_emer_male_child=fi("adm_emer_male_child"), adm_emer_female_child=fi("adm_emer_female_child"),
            mlc_male=fi("mlc_male"), mlc_female=fi("mlc_female"),
            mlc_male_child=fi("mlc_male_child"), mlc_female_child=fi("mlc_female_child"),
            sdd_male=fi("sdd_male"), sdd_female=fi("sdd_female"),
            sdd_male_child=fi("sdd_male_child"), sdd_female_child=fi("sdd_female_child"),
            tubec_male=fi("tubec_male"), tubec_female=fi("tubec_female"),
            tubec_male_child=fi("tubec_male_child"), tubec_female_child=fi("tubec_female_child"),
            vasec_male=fi("vasec_male"), vasec_female=fi("vasec_female"),
            vasec_male_child=fi("vasec_male_child"), vasec_female_child=fi("vasec_female_child"),
            minor_surg_male=fi("minor_surg_male"), minor_surg_female=fi("minor_surg_female"),
            minor_surg_male_child=fi("minor_surg_male_child"), minor_surg_female_child=fi("minor_surg_female_child"),
            major_surg_male=fi("major_surg_male"), major_surg_female=fi("major_surg_female"),
            major_surg_male_child=fi("major_surg_male_child"), major_surg_female_child=fi("major_surg_female_child"),
            deaths_male=fi("deaths_male"), deaths_female=fi("deaths_female"),
            deaths_male_child=fi("deaths_male_child"), deaths_female_child=fi("deaths_female_child"),
            normal_deliveries=fi("normal_deliveries"), caesarean_deliveries=fi("caesarean_deliveries"),
            male_children=fi("male_children"), female_children=fi("female_children"),
            lab_tests=fi("lab_tests"), cumulative_inpatient_days=fi("cumulative_inpatient_days"),
            user_charges_collection=fi("user_charges_collection"), rsby_cases=fi("rsby_cases"),
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(report)
        db.session.commit()

        flash("Hospital report submitted.", "success")
        return redirect(url_for("hospital_reports"))

    return render_template("hospital_report_form.html", user=user)


@app.route("/hospital/reports")
@login_required
def hospital_reports():
    user = current_user()
    reports = HospitalReport.query.filter_by(user_id=user.id).order_by(HospitalReport.created_at.desc()).all()
    return render_template("hospital_reports.html", user=user, reports=reports)


@app.route("/morbidity/report/new", methods=["GET", "POST"])
@login_required
def new_morbidity_report():
    user = current_user()
    if request.method == "POST":
        health_institution_name = request.form.get("health_institution_name", "").strip()
        month_year = request.form.get("month_year", "").strip()

        if not all([health_institution_name, month_year]):
            flash("Health institution name and month/year are required.", "danger")
            return redirect(url_for("new_morbidity_report"))

        report = MorbidityReport(
            user_id=user.id,
            health_institution_name=health_institution_name,
            month_year=month_year,
            entries_json=json.dumps(build_morbidity_payload(request.form)),
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(report)
        db.session.commit()
        flash("Morbidity and mortality report submitted.", "success")
        return redirect(url_for("morbidity_reports"))

    return render_template("morbidity_report_form.html", user=user, diseases=MORBIDITY_DISEASES)


@app.route("/morbidity/reports")
@login_required
def morbidity_reports():
    user = current_user()
    reports = MorbidityReport.query.filter_by(user_id=user.id).order_by(MorbidityReport.created_at.desc()).all()
    return render_template("morbidity_reports.html", user=user, reports=reports)


@app.route("/reports/consolidated")
@login_required
def consolidated_reports():
    user = current_user()
    hospital_reports = HospitalReport.query.filter_by(user_id=user.id).order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.filter_by(user_id=user.id).order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list)
    return render_template("consolidated_reports.html", user=user, rows=rows, show_owner=False, title="My Consolidated Reports")


@app.route("/reports/consolidated/print")
@login_required
def consolidated_reports_print():
    user = current_user()
    hospital_reports = HospitalReport.query.filter_by(user_id=user.id).order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.filter_by(user_id=user.id).order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list)
    return render_template("consolidated_reports_print.html", rows=rows, show_owner=False, title="My Consolidated Reports")


@app.route("/reports/consolidated/export/csv")
@login_required
def consolidated_reports_csv():
    user = current_user()
    hospital_reports = HospitalReport.query.filter_by(user_id=user.id).order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.filter_by(user_id=user.id).order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["report_type", "institution", "district", "month_year", "metric_one_label", "metric_one", "metric_two_label", "metric_two", "created_at"])
    for row in rows:
        writer.writerow([
            row["report_type"], row["institution"], row["district"], row["month_year"],
            row["metric_one_label"], row["metric_one"], row["metric_two_label"], row["metric_two"],
            row["created_at"].isoformat(),
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=consolidated_reports.csv"
    return response


@app.route("/reports/consolidated/export/excel")
@login_required
def consolidated_reports_excel():
    user = current_user()
    hospital_reports = HospitalReport.query.filter_by(user_id=user.id).order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.filter_by(user_id=user.id).order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list)
    output = build_consolidated_excel("My Consolidated Reports", rows)

    response = make_response(output.read())
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = "attachment; filename=consolidated_reports.xlsx"
    return response


@app.route("/morbidity/report/<int:report_id>")
@login_required
def morbidity_report_view(report_id):
    user = current_user()
    report = MorbidityReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission to view this report.", "danger")
        return redirect(url_for("morbidity_reports"))

    rows, total_opd, total_ipd = morbidity_rows(report)
    return render_template(
        "morbidity_report_view.html",
        user=user,
        report=report,
        rows=rows,
        total_opd=total_opd,
        total_ipd=total_ipd,
    )


@app.route("/morbidity/report/<int:report_id>/print")
@login_required
def morbidity_report_print(report_id):
    user = current_user()
    report = MorbidityReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission.", "danger")
        return redirect(url_for("morbidity_reports"))

    rows, total_opd, total_ipd = morbidity_rows(report)
    return render_template("morbidity_report_print.html", report=report, rows=rows, total_opd=total_opd, total_ipd=total_ipd)


@app.route("/morbidity/report/<int:report_id>/export/csv")
@login_required
def morbidity_report_csv(report_id):
    user = current_user()
    report = MorbidityReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission.", "danger")
        return redirect(url_for("morbidity_reports"))

    rows, total_opd, total_ipd = morbidity_rows(report)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["PROFORMA II"])
    writer.writerow(["MORBIDITY AND MORTALITY REPORT"])
    writer.writerow([f"Name of the Health Institution: {report.health_institution_name}", "", f"Month & Year: {report.month_year}"])
    writer.writerow(["Sr. No.", "Name of the disease", "OPD", "IPD"])
    for row in rows:
        writer.writerow([row["sr_no"], row["disease_name"], row["opd"], row["ipd"]])
    writer.writerow(["", "Total", total_opd, total_ipd])
    if report.notes:
        writer.writerow([])
        writer.writerow(["Notes", report.notes])

    filename = f"{report.health_institution_name}_{report.month_year}_morbidity_report.csv".replace(" ", "_")
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.route("/morbidity/report/<int:report_id>/export/excel")
@login_required
def morbidity_report_excel(report_id):
    user = current_user()
    report = MorbidityReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission.", "danger")
        return redirect(url_for("morbidity_reports"))

    rows, total_opd, total_ipd = morbidity_rows(report)
    output = create_morbidity_excel(report, rows, total_opd, total_ipd)
    filename = f"{report.health_institution_name}_{report.month_year}_morbidity_report.xlsx".replace(" ", "_")
    response = make_response(output.read())
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.route("/hospital/report/<int:report_id>")
@login_required
def hospital_report_view(report_id):
    user = current_user()
    report = HospitalReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission to view this report.", "danger")
        return redirect(url_for("hospital_reports"))
    return render_template("hospital_report_view.html", user=user, report=report)


@app.route("/hospital/report/<int:report_id>/print")
@login_required
def hospital_report_print(report_id):
    user = current_user()
    report = HospitalReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission.", "danger")
        return redirect(url_for("hospital_reports"))
    return render_template("hospital_report_print.html", report=report)


@app.route("/hospital/report/<int:report_id>/export/csv")
@login_required
def hospital_report_csv(report_id):
    user = current_user()
    report = HospitalReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission.", "danger")
        return redirect(url_for("hospital_reports"))

    output = io.StringIO()
    writer = csv.writer(output)
    # Header row
    writer.writerow(["HP Indicator", "Male", "Female", "Male Child <14", "Female Child <14", "Total"])
    rows = [
        ("NO. OF OUTPATIENTS: NEW", report.op_new_male, report.op_new_female, report.op_new_male_child, report.op_new_female_child),
        ("NO. OF OUTPATIENTS: OLD", report.op_old_male, report.op_old_female, report.op_old_male_child, report.op_old_female_child),
        ("NO. OF OUTPATIENTS: EMERGENCY", report.op_emer_male, report.op_emer_female, report.op_emer_male_child, report.op_emer_female_child),
        ("OUTPATIENTS TOTAL",
         (report.op_new_male+report.op_old_male+report.op_emer_male),
         (report.op_new_female+report.op_old_female+report.op_emer_female),
         (report.op_new_male_child+report.op_old_male_child+report.op_emer_male_child),
         (report.op_new_female_child+report.op_old_female_child+report.op_emer_female_child)),
        ("NO. OF ADMISSIONS DURING THE MONTH", report.adm_male, report.adm_female, report.adm_male_child, report.adm_female_child),
        ("NO. OF ADMISSIONS THROUGH EMERGENCY (OUT OF 2)", report.adm_emer_male, report.adm_emer_female, report.adm_emer_male_child, report.adm_emer_female_child),
        ("NO. OF MEDICAL LEGAL CASES ADMITTED (OUT OF 2)", report.mlc_male, report.mlc_female, report.mlc_male_child, report.mlc_female_child),
        ("NO. OF PATIENTS ADMITTED & DISCHARGED SAME DAY (OUT OF 2)", report.sdd_male, report.sdd_female, report.sdd_male_child, report.sdd_female_child),
        ("NO. OF TUBECTOMIES INCLUDING LAPAROSCOPIC", report.tubec_male, report.tubec_female, report.tubec_male_child, report.tubec_female_child),
        ("NO. OF VASECTOMIES", report.vasec_male, report.vasec_female, report.vasec_male_child, report.vasec_female_child),
        ("NO. OF MINOR SURGERIES (EXC. VASECTOMIES)", report.minor_surg_male, report.minor_surg_female, report.minor_surg_male_child, report.minor_surg_female_child),
        ("NO. OF MAJOR SURGERIES (EXC. TUBECTOMIES)", report.major_surg_male, report.major_surg_female, report.major_surg_male_child, report.major_surg_female_child),
        ("TOTAL NO. OF SURGERIES",
         report.tubec_male+report.vasec_male+report.minor_surg_male+report.major_surg_male,
         report.tubec_female+report.vasec_female+report.minor_surg_female+report.major_surg_female,
         report.tubec_male_child+report.vasec_male_child+report.minor_surg_male_child+report.major_surg_male_child,
         report.tubec_female_child+report.vasec_female_child+report.minor_surg_female_child+report.major_surg_female_child),
        ("NO. OF DEATHS", report.deaths_male, report.deaths_female, report.deaths_male_child, report.deaths_female_child),
    ]
    for label, m, f, mc, fc in rows:
        writer.writerow([label, m, f, mc, fc, m+f+mc+fc])
    writer.writerow([])
    writer.writerow(["NO. OF NORMAL DELIVERIES", report.normal_deliveries])
    writer.writerow(["NO. OF CAESAREAN DELIVERIES", report.caesarean_deliveries])
    writer.writerow(["TOTAL NO. OF DELIVERIES", report.normal_deliveries + report.caesarean_deliveries])
    writer.writerow(["MALE CH (EXC. STILL BIRTH OUT OF 15)", report.male_children])
    writer.writerow(["FEMALE CH (EXC. STILL BIRTH OUT OF 15)", report.female_children])
    writer.writerow(["NO. OF LAB-TESTS", report.lab_tests])
    writer.writerow(["TOTAL NO. OF CUMULATIVE INPATIENTS DAYS", report.cumulative_inpatient_days])
    writer.writerow(["USER CHARGES COLLECTION (Rs.)", report.user_charges_collection])
    writer.writerow(["NUMBER OF RSBY CASES", report.rsby_cases])
    if report.notes:
        writer.writerow(["NOTES", report.notes])

    fname = f"{report.hospital_name}_{report.month_year}_report.csv".replace(" ", "_")
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={fname}"
    return response


@app.route("/hospital/report/<int:report_id>/export/excel")
@login_required
def hospital_report_excel(report_id):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    import openpyxl

    user = current_user()
    report = HospitalReport.query.get_or_404(report_id)
    if report.user_id != user.id:
        flash("You do not have permission.", "danger")
        return redirect(url_for("hospital_reports"))

    wb = Workbook()
    ws = wb.active
    ws.title = "HP Report"

    hdr_fill = PatternFill("solid", fgColor="C2410C")
    hdr_font = Font(bold=True, color="FFFFFF", size=10)
    sec_fill = PatternFill("solid", fgColor="FFF3E0")
    sec_font = Font(bold=True, size=10)
    tot_fill = PatternFill("solid", fgColor="FED7AA")
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    def cell(row, col, val, fill=None, font=None, align=None):
        c = ws.cell(row=row, column=col, value=val)
        c.border = border
        if fill: c.fill = fill
        if font: c.font = font
        c.alignment = align or center
        return c

    # Title
    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = f"Hospital Performance Report — {report.hospital_name} | {report.district} | {report.month_year}"
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal="center")

    # Column headers
    headers = ["HP Indicator", "MALE", "FEMALE", "MALE CHILD <14 YRS", "FEMALE CHILD <14 YRS", "TOTAL"]
    for ci, h in enumerate(headers, 1):
        cell(2, ci, h, hdr_fill, hdr_font, center)

    def add_row(row_num, label, m, f, mc, fc, fill=None):
        cell(row_num, 1, label, fill, align=left)
        for ci, v in enumerate([m, f, mc, fc, m+f+mc+fc], 2):
            cell(row_num, ci, v, fill, align=center)

    r = 3
    add_row(r, "NO. OF OUTPATIENTS: NEW", report.op_new_male, report.op_new_female, report.op_new_male_child, report.op_new_female_child); r+=1
    add_row(r, "OLD", report.op_old_male, report.op_old_female, report.op_old_male_child, report.op_old_female_child); r+=1
    add_row(r, "EMERGENCY", report.op_emer_male, report.op_emer_female, report.op_emer_male_child, report.op_emer_female_child); r+=1
    op_tm = report.op_new_male+report.op_old_male+report.op_emer_male
    op_tf = report.op_new_female+report.op_old_female+report.op_emer_female
    op_tmc = report.op_new_male_child+report.op_old_male_child+report.op_emer_male_child
    op_tfc = report.op_new_female_child+report.op_old_female_child+report.op_emer_female_child
    add_row(r, "TOTAL", op_tm, op_tf, op_tmc, op_tfc, tot_fill); r+=1
    add_row(r, "NO. OF ADMISSIONS DURING THE MONTH", report.adm_male, report.adm_female, report.adm_male_child, report.adm_female_child); r+=1
    add_row(r, "NO. OF ADMISSIONS THROUGH EMERGENCY (OUT OF 2)", report.adm_emer_male, report.adm_emer_female, report.adm_emer_male_child, report.adm_emer_female_child); r+=1
    add_row(r, "NO. OF MEDICAL LEGAL CASES ADMITTED (OUT OF 2)", report.mlc_male, report.mlc_female, report.mlc_male_child, report.mlc_female_child); r+=1
    add_row(r, "NO. OF PATIENTS ADMITTED & DISCHARGED SAME DAY (OUT OF 2)", report.sdd_male, report.sdd_female, report.sdd_male_child, report.sdd_female_child); r+=1
    add_row(r, "NO. OF TUBECTOMIES INCLUDING LAPAROSCOPIC", report.tubec_male, report.tubec_female, report.tubec_male_child, report.tubec_female_child); r+=1
    add_row(r, "NO. OF VASECTOMIES", report.vasec_male, report.vasec_female, report.vasec_male_child, report.vasec_female_child); r+=1
    add_row(r, "NO. OF MINOR SURGERIES (EXC. VASECTOMIES)", report.minor_surg_male, report.minor_surg_female, report.minor_surg_male_child, report.minor_surg_female_child); r+=1
    add_row(r, "NO. OF MAJOR SURGERIES (EXC. TUBECTOMIES)", report.major_surg_male, report.major_surg_female, report.major_surg_male_child, report.major_surg_female_child); r+=1
    st_m = report.tubec_male+report.vasec_male+report.minor_surg_male+report.major_surg_male
    st_f = report.tubec_female+report.vasec_female+report.minor_surg_female+report.major_surg_female
    st_mc = report.tubec_male_child+report.vasec_male_child+report.minor_surg_male_child+report.major_surg_male_child
    st_fc = report.tubec_female_child+report.vasec_female_child+report.minor_surg_female_child+report.major_surg_female_child
    add_row(r, "TOTAL NO. OF SURGERIES (5+6+7+8)", st_m, st_f, st_mc, st_fc, tot_fill); r+=1
    add_row(r, "NO. OF DEATHS (mention maternal & infant in notes)", report.deaths_male, report.deaths_female, report.deaths_male_child, report.deaths_female_child); r+=1

    # Single-value rows
    single_rows = [
        ("NO. OF NORMAL DELIVERIES", report.normal_deliveries),
        ("NO. OF CAESAREAN DELIVERIES", report.caesarean_deliveries),
        ("TOTAL NO. OF DELIVERIES (13+14)", report.normal_deliveries + report.caesarean_deliveries),
        ("MALE CH (EXCLUDING STILL BIRTH OUT OF 15)", report.male_children),
        ("FEMALE CH (EXCLUDING STILL BIRTH OUT OF 15)", report.female_children),
        ("NO. OF LAB-TESTS", report.lab_tests),
        ("TOTAL NO. OF CUMULATIVE INPATIENTS DAYS", report.cumulative_inpatient_days),
        ("USER CHARGES COLLECTION DURING THE MONTH (Rs.)", report.user_charges_collection),
        ("NUMBER OF RSBY CASES DURING THE MONTH", report.rsby_cases),
    ]
    for label, val in single_rows:
        cell(r, 1, label, align=left)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        c2 = ws.cell(row=r, column=2, value=val)
        c2.border = border
        c2.alignment = center
        r += 1

    if report.notes:
        cell(r, 1, "NOTES", align=left)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        cn = ws.cell(row=r, column=2, value=report.notes)
        cn.border = border
        cn.alignment = left

    ws.column_dimensions["A"].width = 48
    for col in ["B", "C", "D", "E", "F"]:
        ws.column_dimensions[col].width = 14

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    fname = f"{report.hospital_name}_{report.month_year}_report.xlsx".replace(" ", "_")
    response = make_response(output.read())
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = f"attachment; filename={fname}"
    return response


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = User.query.filter_by(username=username).first()
        if admin and admin.is_admin and admin.check_password(password):
            if not admin.is_active:
                flash("Admin account is inactive.", "danger")
                return redirect(url_for("admin_login"))
            session["admin_id"] = admin.id
            flash(f"Welcome Admin, {admin.username}.", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials.", "danger")
        return redirect(url_for("admin_login"))

    return render_template("admin_login.html", user=current_user())


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    admin = current_admin()
    users = User.query.order_by(User.created_at.desc()).all()
    reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports = MorbidityReport.query.order_by(MorbidityReport.created_at.desc()).all()
    stats = {
        "total_users": len(users),
        "total_reports": len(reports) + len(morbidity_reports),
        "total_hospital_reports": len(reports),
        "total_morbidity_reports": len(morbidity_reports),
        "total_outpatients": sum(total_hospital_outpatients(r) for r in reports),
    }
    return render_template(
        "admin_dashboard.html",
        user=current_user(),
        admin=admin,
        users=users,
        reports=reports,
        morbidity_reports=morbidity_reports,
        stats=stats,
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", user=current_user(), admin=current_admin(), users=users)


@app.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
def admin_user_create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        is_admin = request.form.get("is_admin") == "on"

        if not all([username, email, password]):
            flash("Username, email, and password are required.", "danger")
            return redirect(url_for("admin_user_create"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("admin_user_create"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("admin_user_create"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("admin_user_create"))

        new_user = User(username=username, email=email, is_admin=is_admin, is_active=True)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash(f"Login ID created for {username}.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_create.html", user=current_user(), admin=current_admin())


@app.route("/admin/users/import", methods=["GET", "POST"])
@admin_required
def admin_users_import():
    if request.method == "POST":
        csv_file = request.files.get("csv_file")
        if not csv_file or not csv_file.filename:
            flash("Please choose a CSV file.", "danger")
            return redirect(url_for("admin_users_import"))

        try:
            csv_text = csv_file.stream.read().decode("utf-8-sig")
        except Exception:
            flash("Could not read CSV file. Use UTF-8 encoding.", "danger")
            return redirect(url_for("admin_users_import"))

        reader = csv.DictReader(io.StringIO(csv_text))
        required_columns = {"username", "email", "password"}
        if not reader.fieldnames:
            flash("CSV is empty or invalid.", "danger")
            return redirect(url_for("admin_users_import"))

        headers = {h.strip().lower() for h in reader.fieldnames if h}
        missing_columns = required_columns - headers
        if missing_columns:
            missing_list = ", ".join(sorted(missing_columns))
            flash(f"Missing required CSV columns: {missing_list}", "danger")
            return redirect(url_for("admin_users_import"))

        created = 0
        skipped = 0
        batch_usernames = set()
        batch_emails = set()

        for row in reader:
            username = (row.get("username") or "").strip()
            email = (row.get("email") or "").strip().lower()
            password = row.get("password") or ""
            is_admin_raw = (row.get("is_admin") or "").strip().lower()
            is_admin = is_admin_raw in {"1", "true", "yes", "y", "on"}

            if not all([username, email, password]):
                skipped += 1
                continue

            if len(password) < 8:
                skipped += 1
                continue

            if username in batch_usernames or email in batch_emails:
                skipped += 1
                continue

            if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
                skipped += 1
                continue

            new_user = User(username=username, email=email, is_admin=is_admin, is_active=True)
            new_user.set_password(password)
            db.session.add(new_user)
            batch_usernames.add(username)
            batch_emails.add(email)
            created += 1

        db.session.commit()
        flash(f"CSV import complete. Created: {created}, Skipped: {skipped}.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_import.html", user=current_user(), admin=current_admin())


@app.route("/admin/users/import/template.csv")
@admin_required
def admin_users_import_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["username", "email", "password", "is_admin"])
    writer.writerow(["staff1", "staff1@example.com", "StrongPass123", "false"])
    writer.writerow(["manager1", "manager1@example.com", "StrongPass123", "true"])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=users_import_template.csv"
    return response


@app.route("/admin/user/<int:user_id>/reset-password", methods=["GET", "POST"])
@admin_required
def admin_user_reset_password(user_id):
    target_user = User.query.get_or_404(user_id)

    if request.method == "POST":
        new_password = request.form.get("password", "")
        if len(new_password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("admin_user_reset_password", user_id=target_user.id))

        target_user.set_password(new_password)
        db.session.commit()
        flash(f"Password reset for {target_user.username}.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_reset_password.html", user=current_user(), admin=current_admin(), target_user=target_user)


@app.route("/admin/user/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def admin_user_toggle_active(user_id):
    target_user = User.query.get_or_404(user_id)
    admin = current_admin()

    if target_user.id == admin.id and target_user.is_active:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin_users"))

    if target_user.is_admin and target_user.is_active:
        active_admin_count = User.query.filter_by(is_admin=True, is_active=True).count()
        if active_admin_count <= 1:
            flash("Cannot deactivate the last active admin.", "danger")
            return redirect(url_for("admin_users"))

    target_user.is_active = not target_user.is_active
    db.session.commit()
    state = "activated" if target_user.is_active else "deactivated"
    flash(f"{target_user.username} has been {state}.", "info")
    return redirect(url_for("admin_users"))


@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_user_delete(user_id):
    target_user = User.query.get_or_404(user_id)
    admin = current_admin()

    if target_user.id == admin.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))

    if target_user.is_admin:
        total_admin_count = User.query.filter_by(is_admin=True).count()
        if total_admin_count <= 1:
            flash("Cannot delete the last admin account.", "danger")
            return redirect(url_for("admin_users"))

    db.session.delete(target_user)
    db.session.commit()
    flash("User deleted successfully.", "info")
    return redirect(url_for("admin_users"))


@app.route("/admin/report/<int:report_id>")
@admin_required
def admin_report_view(report_id):
    report = HospitalReport.query.get_or_404(report_id)
    return render_template("admin_report_view.html", user=current_user(), admin=current_admin(), report=report)


@app.route("/admin/report/<int:report_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_report_edit(report_id):
    report = HospitalReport.query.get_or_404(report_id)

    if request.method == "POST":
        report.hospital_name = request.form.get("hospital_name", "").strip()
        report.district = request.form.get("district", "").strip()
        report.month_year = request.form.get("month_year", "").strip()

        if not all([report.hospital_name, report.district, report.month_year]):
            flash("Hospital name, district, and month/year are required.", "danger")
            return redirect(url_for("admin_report_edit", report_id=report.id))

        def fi(name):
            return request.form.get(name, 0, type=int)

        report.op_new_male=fi("op_new_male"); report.op_new_female=fi("op_new_female")
        report.op_new_male_child=fi("op_new_male_child"); report.op_new_female_child=fi("op_new_female_child")
        report.op_old_male=fi("op_old_male"); report.op_old_female=fi("op_old_female")
        report.op_old_male_child=fi("op_old_male_child"); report.op_old_female_child=fi("op_old_female_child")
        report.op_emer_male=fi("op_emer_male"); report.op_emer_female=fi("op_emer_female")
        report.op_emer_male_child=fi("op_emer_male_child"); report.op_emer_female_child=fi("op_emer_female_child")
        report.adm_male=fi("adm_male"); report.adm_female=fi("adm_female")
        report.adm_male_child=fi("adm_male_child"); report.adm_female_child=fi("adm_female_child")
        report.adm_emer_male=fi("adm_emer_male"); report.adm_emer_female=fi("adm_emer_female")
        report.adm_emer_male_child=fi("adm_emer_male_child"); report.adm_emer_female_child=fi("adm_emer_female_child")
        report.mlc_male=fi("mlc_male"); report.mlc_female=fi("mlc_female")
        report.mlc_male_child=fi("mlc_male_child"); report.mlc_female_child=fi("mlc_female_child")
        report.sdd_male=fi("sdd_male"); report.sdd_female=fi("sdd_female")
        report.sdd_male_child=fi("sdd_male_child"); report.sdd_female_child=fi("sdd_female_child")
        report.tubec_male=fi("tubec_male"); report.tubec_female=fi("tubec_female")
        report.tubec_male_child=fi("tubec_male_child"); report.tubec_female_child=fi("tubec_female_child")
        report.vasec_male=fi("vasec_male"); report.vasec_female=fi("vasec_female")
        report.vasec_male_child=fi("vasec_male_child"); report.vasec_female_child=fi("vasec_female_child")
        report.minor_surg_male=fi("minor_surg_male"); report.minor_surg_female=fi("minor_surg_female")
        report.minor_surg_male_child=fi("minor_surg_male_child"); report.minor_surg_female_child=fi("minor_surg_female_child")
        report.major_surg_male=fi("major_surg_male"); report.major_surg_female=fi("major_surg_female")
        report.major_surg_male_child=fi("major_surg_male_child"); report.major_surg_female_child=fi("major_surg_female_child")
        report.deaths_male=fi("deaths_male"); report.deaths_female=fi("deaths_female")
        report.deaths_male_child=fi("deaths_male_child"); report.deaths_female_child=fi("deaths_female_child")
        report.normal_deliveries=fi("normal_deliveries"); report.caesarean_deliveries=fi("caesarean_deliveries")
        report.male_children=fi("male_children"); report.female_children=fi("female_children")
        report.lab_tests=fi("lab_tests"); report.cumulative_inpatient_days=fi("cumulative_inpatient_days")
        report.user_charges_collection=fi("user_charges_collection"); report.rsby_cases=fi("rsby_cases")
        report.notes = request.form.get("notes", "").strip()

        db.session.commit()
        flash("Report updated successfully.", "success")
        return redirect(url_for("admin_report_view", report_id=report.id))

    return render_template("admin_report_edit.html", user=current_user(), admin=current_admin(), report=report)


@app.route("/admin/report/<int:report_id>/delete", methods=["POST"])
@admin_required
def admin_report_delete(report_id):
    report = HospitalReport.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash("Report deleted.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reports/export.csv")
@admin_required
def admin_reports_export():
    reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "hospital_name", "district", "month_year", "owner_username", "owner_email",
        "op_new_male", "op_new_female", "op_new_male_child", "op_new_female_child",
        "op_old_male", "op_old_female", "op_old_male_child", "op_old_female_child",
        "op_emer_male", "op_emer_female", "op_emer_male_child", "op_emer_female_child",
        "adm_male", "adm_female", "adm_male_child", "adm_female_child",
        "adm_emer_male", "adm_emer_female", "adm_emer_male_child", "adm_emer_female_child",
        "mlc_male", "mlc_female", "mlc_male_child", "mlc_female_child",
        "sdd_male", "sdd_female", "sdd_male_child", "sdd_female_child",
        "tubec_male", "tubec_female", "tubec_male_child", "tubec_female_child",
        "vasec_male", "vasec_female", "vasec_male_child", "vasec_female_child",
        "minor_surg_male", "minor_surg_female", "minor_surg_male_child", "minor_surg_female_child",
        "major_surg_male", "major_surg_female", "major_surg_male_child", "major_surg_female_child",
        "deaths_male", "deaths_female", "deaths_male_child", "deaths_female_child",
        "normal_deliveries", "caesarean_deliveries", "male_children", "female_children",
        "lab_tests", "cumulative_inpatient_days", "user_charges_collection", "rsby_cases",
        "notes", "created_at",
    ])
    for r in reports:
        writer.writerow([
            r.id, r.hospital_name, r.district, r.month_year,
            r.owner.username, r.owner.email,
            r.op_new_male, r.op_new_female, r.op_new_male_child, r.op_new_female_child,
            r.op_old_male, r.op_old_female, r.op_old_male_child, r.op_old_female_child,
            r.op_emer_male, r.op_emer_female, r.op_emer_male_child, r.op_emer_female_child,
            r.adm_male, r.adm_female, r.adm_male_child, r.adm_female_child,
            r.adm_emer_male, r.adm_emer_female, r.adm_emer_male_child, r.adm_emer_female_child,
            r.mlc_male, r.mlc_female, r.mlc_male_child, r.mlc_female_child,
            r.sdd_male, r.sdd_female, r.sdd_male_child, r.sdd_female_child,
            r.tubec_male, r.tubec_female, r.tubec_male_child, r.tubec_female_child,
            r.vasec_male, r.vasec_female, r.vasec_male_child, r.vasec_female_child,
            r.minor_surg_male, r.minor_surg_female, r.minor_surg_male_child, r.minor_surg_female_child,
            r.major_surg_male, r.major_surg_female, r.major_surg_male_child, r.major_surg_female_child,
            r.deaths_male, r.deaths_female, r.deaths_male_child, r.deaths_female_child,
            r.normal_deliveries, r.caesarean_deliveries, r.male_children, r.female_children,
            r.lab_tests, r.cumulative_inpatient_days, r.user_charges_collection, r.rsby_cases,
            r.notes, r.created_at.isoformat(),
        ])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=hospital_reports.csv"
    return response


@app.route("/admin/morbidity-report/<int:report_id>")
@admin_required
def admin_morbidity_report_view(report_id):
    report = MorbidityReport.query.get_or_404(report_id)
    rows, total_opd, total_ipd = morbidity_rows(report)
    return render_template(
        "admin_morbidity_report_view.html",
        user=current_user(),
        admin=current_admin(),
        report=report,
        rows=rows,
        total_opd=total_opd,
        total_ipd=total_ipd,
    )


@app.route("/admin/morbidity-report/<int:report_id>/delete", methods=["POST"])
@admin_required
def admin_morbidity_report_delete(report_id):
    report = MorbidityReport.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash("Morbidity report deleted.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/morbidity-reports/export.csv")
@admin_required
def admin_morbidity_reports_export():
    reports = MorbidityReport.query.order_by(MorbidityReport.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "health_institution_name", "month_year", "owner_username", "owner_email", "sr_no", "disease_name", "opd", "ipd", "notes", "created_at"])
    for report in reports:
        rows, _, _ = morbidity_rows(report)
        for row in rows:
            writer.writerow([
                report.id,
                report.health_institution_name,
                report.month_year,
                report.morbidity_owner.username,
                report.morbidity_owner.email,
                row["sr_no"],
                row["disease_name"],
                row["opd"],
                row["ipd"],
                report.notes,
                report.created_at.isoformat(),
            ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=morbidity_reports.csv"
    return response


@app.route("/admin/reports/consolidated")
@admin_required
def admin_consolidated_reports():
    hospital_reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list, include_owner=True)
    return render_template("consolidated_reports.html", user=current_user(), rows=rows, show_owner=True, title="Admin Consolidated Reports")


@app.route("/admin/reports/consolidated/print")
@admin_required
def admin_consolidated_reports_print():
    hospital_reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list, include_owner=True)
    return render_template("consolidated_reports_print.html", rows=rows, show_owner=True, title="Admin Consolidated Reports")


@app.route("/admin/reports/consolidated/export/csv")
@admin_required
def admin_consolidated_reports_csv():
    hospital_reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list, include_owner=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["report_type", "institution", "district", "month_year", "metric_one_label", "metric_one", "metric_two_label", "metric_two", "owner_username", "owner_email", "created_at"])
    for row in rows:
        writer.writerow([
            row["report_type"], row["institution"], row["district"], row["month_year"],
            row["metric_one_label"], row["metric_one"], row["metric_two_label"], row["metric_two"],
            row["owner_username"], row["owner_email"], row["created_at"].isoformat(),
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=admin_consolidated_reports.csv"
    return response


@app.route("/admin/reports/consolidated/export/excel")
@admin_required
def admin_consolidated_reports_excel():
    hospital_reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).all()
    morbidity_reports_list = MorbidityReport.query.order_by(MorbidityReport.created_at.desc()).all()
    rows = build_consolidated_rows(hospital_reports, morbidity_reports_list, include_owner=True)
    output = build_consolidated_excel("Admin Consolidated Reports", rows, include_owner=True)

    response = make_response(output.read())
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = "attachment; filename=admin_consolidated_reports.xlsx"
    return response


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("admin_login"))


def initialize_database() -> None:
    with app.app_context():
        # Migrate hospital_report table if schema is outdated
        try:
            result = db.session.execute(text("PRAGMA table_info(hospital_report)")).fetchall()
            if result:
                existing_cols = {row[1] for row in result}
                if "op_new_male" not in existing_cols:
                    db.session.execute(text("DROP TABLE hospital_report"))
                    db.session.commit()
        except Exception:
            db.session.rollback()

        db.create_all()

        # Lightweight migration for existing SQLite DBs created before is_active existed.
        try:
            result = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
            user_columns = [row[1] for row in result]
            if "is_active" not in user_columns:
                db.session.execute(text("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                db.session.execute(text("UPDATE user SET is_active = 1 WHERE is_active IS NULL"))
                db.session.commit()
        except Exception:
            db.session.rollback()

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@nova.local")
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123")

        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(username=admin_username, email=admin_email, is_admin=True)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()


initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
