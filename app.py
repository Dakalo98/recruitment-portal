import os
import sqlite3
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session
)
from flask_cors import CORS

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "recruitment.db")

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change to a real secret in production
CORS(app)


def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Create jobs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            apply_link TEXT NOT NULL
        )
    ''')

    # Create admins table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Insert default admin if none exists
    c.execute("SELECT COUNT(*) FROM admins")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO admins (email, password) VALUES (?, ?)", ("admin@example.com", "admin123"))

    # Insert sample jobs if none exist
    c.execute("SELECT COUNT(*) FROM jobs")
    if c.fetchone()[0] == 0:
        jobs = [
            ("SITA IT Technician", "SITA", "https://www.sita.co.za/sites/default/files/End%20User%20Computing%20Technician%20_2.pdf"),
            ("Web Developer", "CodeWorks", "https://codeworks.dev/careers/apply"),
            ("System Administrator", "NetSolutions", "https://netsolutions.com/careers/456")
        ]
        c.executemany("INSERT INTO jobs (title, company, apply_link) VALUES (?, ?, ?)", jobs)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/jobs")
def jobs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs")
    jobs_list = c.fetchall()
    conn.close()
    return render_template("jobs.html", jobs=jobs_list)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE email=? AND password=?", (email, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session['admin'] = email
            flash("Logged in successfully!", "success")
            return redirect(url_for("admin_jobs"))
        else:
            flash("Invalid credentials", "error")
            return render_template("admin_login.html")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop('admin', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("admin_login"))


def admin_required(func):
    """Decorator to protect admin routes."""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            flash("Please login to access admin area", "error")
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)

    return wrapper


@app.route("/admin/jobs")
@admin_required
def admin_jobs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs")
    jobs_list = c.fetchall()
    conn.close()
    return render_template("admin_jobs.html", jobs=jobs_list)


@app.route("/admin/jobs/add", methods=["GET", "POST"])
@admin_required
def admin_add_job():
    if request.method == "POST":
        title = request.form['title'].strip()
        company = request.form['company'].strip()
        apply_link = request.form['apply_link'].strip()

        if not title or not company or not apply_link:
            flash("All fields are required.", "error")
            return render_template("admin_add_job.html")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO jobs (title, company, apply_link) VALUES (?, ?, ?)", (title, company, apply_link))
        conn.commit()
        conn.close()

        flash("Job added successfully!", "success")
        return redirect(url_for("admin_jobs"))

    return render_template("admin_add_job.html")


@app.route("/admin/jobs/edit/<int:job_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_job(job_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    job = c.fetchone()

    if not job:
        conn.close()
        flash("Job not found.", "error")
        return redirect(url_for("admin_jobs"))

    if request.method == "POST":
        title = request.form['title'].strip()
        company = request.form['company'].strip()
        apply_link = request.form['apply_link'].strip()

        if not title or not company or not apply_link:
            flash("All fields are required.", "error")
            return render_template("admin_edit_job.html", job=job)

        c.execute("UPDATE jobs SET title=?, company=?, apply_link=? WHERE id=?", (title, company, apply_link, job_id))
        conn.commit()
        conn.close()
        flash("Job updated successfully!", "success")
        return redirect(url_for("admin_jobs"))

    conn.close()
    return render_template("admin_edit_job.html", job=job)


@app.route("/admin/jobs/delete/<int:job_id>", methods=["GET", "POST"])
@admin_required
def admin_delete_job(job_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    job = c.fetchone()

    if not job:
        conn.close()
        flash("Job not found.", "error")
        return redirect(url_for("admin_jobs"))

    if request.method == "POST":
        c.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
        conn.close()
        flash("Job deleted successfully!", "success")
        return redirect(url_for("admin_jobs"))

    conn.close()
    # Convert tuple to dict for convenience in template
    job_dict = {"id": job[0], "title": job[1], "company": job[2], "apply_link": job[3]}
    return render_template("admin_delete_job.html", job=job_dict)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=5000, debug=True)
