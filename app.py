import io
import os
import csv
import base64
import datetime
from flask import Flask, render_template, request, redirect, session, flash, send_file, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "yogesh_secret_key"

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Folder create karein agar nahi hai
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db_config = {
    'host': "localhost",
    'port': 3300,
    'user': "root",
    'password': "password",
    'database': "staff_system"
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- SETUP DB ---
def init_db():
    # ... (purana logic same rahega user creation ka)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE, password_hash VARCHAR(255))")
    cursor.execute("SELECT * FROM users WHERE username = 'yogesh'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash("yogesh07")
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", ('yogesh', hashed_pw))
        conn.commit()
    conn.close()

# --- ROUTES ---

@app.route("/")
def index():
    return redirect("/dashboard") if "user" in session else redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session["user"] = user['username']
            return redirect("/dashboard")
        else:
            flash("Invalid Credentials!", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect("/login")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) as count FROM employees")
    total = cursor.fetchone()['count']
    
    # Attendance Today Count
    today = datetime.date.today()
    cursor.execute("SELECT COUNT(*) as count FROM attendance WHERE date = %s AND status = 'Present'", (today,))
    present_today = cursor.fetchone()['count']

    cursor.execute("SELECT department, COUNT(*) as count FROM employees GROUP BY department")
    data = cursor.fetchall()
    conn.close()

    depts = [row['department'] for row in data if row['department']]
    counts = [row['count'] for row in data if row['department']]
    plot_url = None
    if depts:
        plt.figure(figsize=(6,4))
        plt.bar(depts, counts, color='#4CAF50')
        plt.tight_layout()
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()

    return render_template("dashboard.html", total=total, present_today=present_today, plot_url=plot_url, username=session['user'])

@app.route("/employees")
def view_employees():
    if "user" not in session: return redirect("/login")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    search = request.args.get("search")
    sql = "SELECT * FROM employees WHERE 1=1"
    params = []
    if search:
        sql += " AND name LIKE %s"
        params.append(f"%{search}%")
    
    cursor.execute(sql, tuple(params))
    employees = cursor.fetchall()
    conn.close()
    return render_template("view_employees.html", employees=employees)

@app.route("/add", methods=["GET", "POST"])
def add_employee():
    if "user" not in session: return redirect("/login")
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        dept = request.form["department"]
        pos = request.form["position"]
        doj = request.form["date_of_joining"]
        
        # IMAGE UPLOAD LOGIC
        filename = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Save unique name to prevent overwrite
                filename = f"{datetime.datetime.now().timestamp()}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO employees (name, email, department, position, date_of_joining, profile_pic) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (name, email, dept, pos, doj, filename))
        conn.commit()
        conn.close()
        flash("Employee Added!", "success")
        return redirect("/employees")
    return render_template("add_employee.html")

# --- NEW FEATURES: Export & Attendance ---

@app.route("/export_csv")
def export_csv():
    if "user" not in session: return redirect("/login")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Department', 'Position', 'Join Date'])
    for emp in employees:
        writer.writerow([emp['id'], emp['name'], emp['email'], emp['department'], emp['position'], emp['date_of_joining']])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='employees_report.csv'
    )

@app.route("/mark_attendance/<int:emp_id>")
def mark_attendance(emp_id):
    if "user" not in session: return redirect("/login")
    today = datetime.date.today()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check duplicate
    cursor.execute("SELECT * FROM attendance WHERE employee_id=%s AND date=%s", (emp_id, today))
    if cursor.fetchone():
        flash("Already marked present today!", "info")
    else:
        cursor.execute("INSERT INTO attendance (employee_id, date, status) VALUES (%s, %s, 'Present')", (emp_id, today))
        conn.commit()
        flash("Attendance Marked!", "success")
    
    conn.close()
    return redirect("/employees")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)