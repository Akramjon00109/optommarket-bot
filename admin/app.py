"""
Admin Panel - Flask Application
System prompt va statistika boshqaruvi.
"""

import os
import json
from pathlib import Path
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_PATH = DATA_DIR / "knowledge_base.json"

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET_KEY", "change-me-in-production")
CORS(app)

# Simple auth credentials from env
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


def login_required(f):
    """Login required decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def load_knowledge_base() -> dict:
    """Load knowledge base from JSON file."""
    if KNOWLEDGE_BASE_PATH.exists():
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_knowledge_base(data: dict) -> bool:
    """Save knowledge base to JSON file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(KNOWLEDGE_BASE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving knowledge base: {e}")
        return False


@app.route("/")
def index():
    """Redirect to login or dashboard."""
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Noto'g'ri login yoki parol"
    
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Logout."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard."""
    kb = load_knowledge_base()
    return render_template("dashboard.html", knowledge_base=kb)


@app.route("/api/knowledge-base", methods=["GET"])
@login_required
def get_knowledge_base():
    """Get knowledge base API."""
    kb = load_knowledge_base()
    return jsonify(kb)


@app.route("/api/knowledge-base", methods=["POST"])
@login_required
def update_knowledge_base():
    """Update knowledge base API."""
    try:
        data = request.get_json()
        if save_knowledge_base(data):
            return jsonify({"success": True, "message": "Saqlandi"})
        else:
            return jsonify({"success": False, "message": "Xatolik yuz berdi"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/company-info", methods=["POST"])
@login_required
def update_company_info():
    """Update company info."""
    try:
        kb = load_knowledge_base()
        kb["company_info"] = request.get_json()
        
        if save_knowledge_base(kb):
            return jsonify({"success": True, "message": "Kompaniya ma'lumotlari yangilandi"})
        else:
            return jsonify({"success": False, "message": "Xatolik yuz berdi"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/tone", methods=["POST"])
@login_required
def update_tone():
    """Update tone of voice."""
    try:
        kb = load_knowledge_base()
        data = request.get_json()
        kb["tone_of_voice"] = data.get("tone_of_voice", "")
        
        if save_knowledge_base(kb):
            return jsonify({"success": True, "message": "Muloqot uslubi yangilandi"})
        else:
            return jsonify({"success": False, "message": "Xatolik yuz berdi"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
