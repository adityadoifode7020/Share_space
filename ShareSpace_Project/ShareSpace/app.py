import os, sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-for-production")
DB_PATH = os.path.join(os.path.dirname(__file__), "sharespace.db")

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def log_action(actor_id, action, details):
    db = get_db()
    db.execute("INSERT INTO audit_log(actor_id, action, details, created_at) VALUES(?,?,?,?)",
               (actor_id, action, details, now()))
    db.commit()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', verified INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS resources(
      id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL REFERENCES users(id),
      name TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL,
      available_from TEXT NOT NULL, available_to TEXT NOT NULL, requirements TEXT DEFAULT '',
      rules TEXT DEFAULT '', deposit REAL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bookings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id INTEGER NOT NULL REFERENCES resources(id),
      user_id INTEGER NOT NULL REFERENCES users(id), start_at TEXT NOT NULL, end_at TEXT NOT NULL,
      purpose TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', owner_note TEXT DEFAULT '',
      initial_condition TEXT DEFAULT '', final_condition TEXT DEFAULT '', checked_in_at TEXT DEFAULT '',
      checked_out_at TEXT DEFAULT '', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS incidents(
      id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER NOT NULL REFERENCES bookings(id),
      reporter_id INTEGER NOT NULL REFERENCES users(id), incident_type TEXT NOT NULL,
      description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INTEGER REFERENCES users(id),
      action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL
    );
    """)
    # Seed demo accounts/resources only on first run
    count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        demo_users = [
          ("Demo Owner", "owner@sharespace.demo", "owner123", "owner", 1, now()),
          ("Demo Student", "student@sharespace.demo", "student123", "user", 1, now()),
          ("Demo Manager", "manager@sharespace.demo", "manager123", "manager", 1, now()),
          ("Demo Admin", "admin@sharespace.demo", "admin123", "admin", 1, now())
        ]
        db.executemany("INSERT INTO users(name,email,password,role,verified,created_at) VALUES(?,?,?,?,?,?)", demo_users)
        owner = db.execute("SELECT id FROM users WHERE email='owner@sharespace.demo'").fetchone()[0]
        db.executemany("""INSERT INTO resources(owner_id,name,category,description,location,available_from,available_to,requirements,rules,deposit,status,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", [
          (owner,"DSLR Camera Kit","Camera & Media","Camera kit with lens, battery and carry case.","Media Lab, Building A","2026-01-01","2027-12-31","Basic camera handling","Return with all accessories; indoor use preferred.",500,"active",now()),
          (owner,"Electronics Workbench","Lab Equipment","Bench with multimeter, regulated power supply and hand tools.","Electronics Lab, Room 204","2026-01-01","2027-12-31","Lab safety induction required","Staff supervision required; no unattended operation.",0,"active",now()),
          (owner,"Seminar Room 2","Space","Small meeting room for project discussions and presentations.","Block B, Floor 1","2026-01-01","2027-12-31","Institution membership","Leave the room clean and reset chairs.",0,"active",now()),
          (owner,"3D Printer","Fabrication","FDM 3D printer for prototypes. Materials supplied separately.","Makerspace, Room 12","2026-01-01","2027-12-31","3D printer training required","Only approved filament; operator must remain present.",300,"active",now())
        ])
    db.commit()
    db.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to perform that action.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.context_processor
def inject_user():
    return {"current_user": session.get("name"), "current_role": session.get("role")}

@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        role = request.form.get("role","user")
        if role not in ("user","owner"):
            role = "user"
        if not name or not email or len(password) < 6:
            flash("Enter your name, email, and a password of at least 6 characters.", "danger")
            return render_template("register.html")
        try:
            db = get_db()
            cur = db.execute("INSERT INTO users(name,email,password,role,verified,created_at) VALUES(?,?,?,?,0,?)",
                             (name,email,password,role,now()))
            db.commit()
            session.update(user_id=cur.lastrowid, name=name, role=role)
            log_action(cur.lastrowid, "REGISTERED", f"Account created with role {role}; verification pending")
            flash("Account created. Your profile is pending verification; some resources may require approval.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("That email address is already registered.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = get_db().execute("SELECT * FROM users WHERE email=? AND password=?", (email,password)).fetchone()
        if user:
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            log_action(user["id"], "LOGIN", "Signed in")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    if session.get("user_id"):
        log_action(session["user_id"], "LOGOUT", "Signed out")
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    resources = db.execute("""SELECT r.*, u.name owner_name FROM resources r JOIN users u ON u.id=r.owner_id
       WHERE r.status='active' ORDER BY r.created_at DESC""").fetchall()
    user_id = session["user_id"]
    if session["role"] in ("owner","manager","admin"):
        bookings = db.execute("""SELECT b.*, r.name resource_name, u.name user_name, r.owner_id
          FROM bookings b JOIN resources r ON r.id=b.resource_id JOIN users u ON u.id=b.user_id
          WHERE r.owner_id=? OR ? IN ('manager','admin') ORDER BY b.created_at DESC""",
          (user_id,session["role"])).fetchall()
    else:
        bookings = db.execute("""SELECT b.*, r.name resource_name, u.name user_name, r.owner_id
          FROM bookings b JOIN resources r ON r.id=b.resource_id JOIN users u ON u.id=b.user_id
          WHERE b.user_id=? ORDER BY b.created_at DESC""",(user_id,)).fetchall()
    stats = {
      "resources": db.execute("SELECT COUNT(*) FROM resources WHERE status='active'").fetchone()[0],
      "pending": db.execute("SELECT COUNT(*) FROM bookings WHERE status='pending'").fetchone()[0],
      "active": db.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('approved','checked_in')").fetchone()[0],
      "incidents": db.execute("SELECT COUNT(*) FROM incidents WHERE status='open'").fetchone()[0]
    }
    return render_template("dashboard.html", resources=resources, bookings=bookings, stats=stats)

@app.route("/resources/new", methods=["GET","POST"])
@login_required
def new_resource():
    if session.get("role") not in ("owner","manager","admin"):
        flash("Only resource owners and managers can list resources.", "warning")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        f = request.form
        required = [f.get(k,"").strip() for k in ("name","category","description","location","available_from","available_to")]
        if not all(required):
            flash("Please complete all required fields.", "danger")
            return render_template("resource_form.html")
        if f["available_to"] < f["available_from"]:
            flash("Availability end date must be after start date.", "danger")
            return render_template("resource_form.html")
        db = get_db()
        cur = db.execute("""INSERT INTO resources(owner_id,name,category,description,location,available_from,available_to,requirements,rules,deposit,status,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          (session["user_id"],f["name"].strip(),f["category"],f["description"].strip(),f["location"].strip(),
           f["available_from"],f["available_to"],f.get("requirements","").strip(),f.get("rules","").strip(),
           max(0,float(f.get("deposit") or 0)),"active",now()))
        db.commit()
        log_action(session["user_id"], "RESOURCE_LISTED", f"Resource #{cur.lastrowid}: {f['name']}")
        flash("Resource listed successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("resource_form.html")

@app.route("/resources/<int:resource_id>")
@login_required
def resource_detail(resource_id):
    resource = get_db().execute("SELECT r.*,u.name owner_name FROM resources r JOIN users u ON u.id=r.owner_id WHERE r.id=?",(resource_id,)).fetchone()
    if not resource:
        flash("Resource not found.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("resource_detail.html", resource=resource)

@app.route("/resources/<int:resource_id>/request", methods=["POST"])
@login_required
def request_booking(resource_id):
    db = get_db()
    resource = db.execute("SELECT * FROM resources WHERE id=? AND status='active'",(resource_id,)).fetchone()
    if not resource:
        flash("This resource is unavailable.", "danger")
        return redirect(url_for("dashboard"))
    start_at, end_at = request.form.get("start_at",""), request.form.get("end_at","")
    purpose = request.form.get("purpose","").strip()
    if not start_at or not end_at or end_at <= start_at or not purpose:
        flash("Provide a valid time range and explain the purpose.", "danger")
        return redirect(url_for("resource_detail", resource_id=resource_id))
    if resource["owner_id"] == session["user_id"]:
        flash("You cannot book your own resource.", "warning")
        return redirect(url_for("resource_detail", resource_id=resource_id))
    if resource["requirements"] and not get_db().execute("SELECT verified FROM users WHERE id=?",(session["user_id"],)).fetchone()["verified"]:
        flash("This resource has eligibility requirements. Your profile must be verified by a manager first.", "warning")
        return redirect(url_for("resource_detail", resource_id=resource_id))
    overlap = db.execute("""SELECT COUNT(*) FROM bookings WHERE resource_id=? AND status IN ('pending','approved','checked_in')
      AND start_at < ? AND end_at > ?""",(resource_id,end_at,start_at)).fetchone()[0]
    status = "waitlisted" if overlap else "pending"
    cur = db.execute("""INSERT INTO bookings(resource_id,user_id,start_at,end_at,purpose,status,created_at)
      VALUES(?,?,?,?,?,?,?)""",(resource_id,session["user_id"],start_at,end_at,purpose,status,now()))
    db.commit()
    log_action(session["user_id"], "BOOKING_REQUESTED" if status=="pending" else "WAITLISTED",
               f"Booking #{cur.lastrowid} for resource #{resource_id}")
    flash("Request submitted for owner review." if status=="pending" else "That time is already requested/booked. You have been added to the waiting list.", "success")
    return redirect(url_for("dashboard"))

@app.route("/bookings/<int:booking_id>/decision", methods=["POST"])
@login_required
def booking_decision(booking_id):
    db = get_db()
    booking = db.execute("""SELECT b.*,r.owner_id,r.name resource_name FROM bookings b JOIN resources r ON r.id=b.resource_id WHERE b.id=?""",(booking_id,)).fetchone()
    if not booking:
        flash("Booking not found.", "danger"); return redirect(url_for("dashboard"))
    if session["role"] not in ("manager","admin") and booking["owner_id"] != session["user_id"]:
        flash("Only the resource owner or a manager can decide this request.", "danger"); return redirect(url_for("dashboard"))
    decision = request.form.get("decision")
    note = request.form.get("owner_note","").strip()
    if decision not in ("approved","rejected","waitlisted"):
        flash("Invalid decision.", "danger"); return redirect(url_for("dashboard"))
    if booking["status"] not in ("pending","waitlisted"):
        flash("This booking has already moved past the decision stage.", "warning"); return redirect(url_for("dashboard"))
    if decision == "approved":
        overlap = db.execute("""SELECT COUNT(*) FROM bookings WHERE resource_id=? AND id<>? AND status IN ('approved','checked_in')
          AND start_at < ? AND end_at > ?""",(booking["resource_id"],booking_id,booking["end_at"],booking["start_at"])).fetchone()[0]
        if overlap:
            flash("Cannot approve: another approved booking overlaps this time. Use the waitlist instead.", "danger")
            return redirect(url_for("dashboard"))
    db.execute("UPDATE bookings SET status=?,owner_note=? WHERE id=?",(decision,note,booking_id))
    db.commit()
    log_action(session["user_id"], "BOOKING_"+decision.upper(), f"Booking #{booking_id}; note: {note or 'none'}")
    flash(f"Booking #{booking_id} marked {decision}.", "success")
    return redirect(url_for("dashboard"))

@app.route("/bookings/<int:booking_id>/checkin", methods=["POST"])
@login_required
def checkin(booking_id):
    db = get_db()
    b = db.execute("SELECT b.*,r.owner_id FROM bookings b JOIN resources r ON r.id=b.resource_id WHERE b.id=?",(booking_id,)).fetchone()
    if not b: flash("Booking not found.", "danger"); return redirect(url_for("dashboard"))
    if session["user_id"] != b["user_id"] and session["user_id"] != b["owner_id"] and session["role"] not in ("manager","admin"):
        flash("You cannot check in this booking.", "danger"); return redirect(url_for("dashboard"))
    condition = request.form.get("condition","").strip()
    if b["status"] != "approved" or not condition:
        flash("Only approved bookings can check in; record the initial condition.", "warning")
        return redirect(url_for("dashboard"))
    db.execute("UPDATE bookings SET status='checked_in',initial_condition=?,checked_in_at=? WHERE id=?",(condition,now(),booking_id))
    db.commit()
    log_action(session["user_id"], "CHECK_IN", f"Booking #{booking_id}; initial condition: {condition}")
    flash("Check-in recorded.", "success")
    return redirect(url_for("dashboard"))

@app.route("/bookings/<int:booking_id>/checkout", methods=["POST"])
@login_required
def checkout(booking_id):
    db = get_db()
    b = db.execute("SELECT b.*,r.owner_id FROM bookings b JOIN resources r ON r.id=b.resource_id WHERE b.id=?",(booking_id,)).fetchone()
    if not b: flash("Booking not found.", "danger"); return redirect(url_for("dashboard"))
    if session["user_id"] != b["user_id"] and session["user_id"] != b["owner_id"] and session["role"] not in ("manager","admin"):
        flash("You cannot check out this booking.", "danger"); return redirect(url_for("dashboard"))
    condition = request.form.get("condition","").strip()
    if b["status"] != "checked_in" or not condition:
        flash("Record the final condition before completing return.", "warning")
        return redirect(url_for("dashboard"))
    db.execute("UPDATE bookings SET status='returned',final_condition=?,checked_out_at=? WHERE id=?",(condition,now(),booking_id))
    db.commit()
    log_action(session["user_id"], "CHECK_OUT_RETURNED", f"Booking #{booking_id}; final condition: {condition}")
    flash("Return recorded. Thank you for completing the resource lifecycle.", "success")
    return redirect(url_for("dashboard"))

@app.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    db = get_db()
    b = db.execute("SELECT * FROM bookings WHERE id=?",(booking_id,)).fetchone()
    if not b: flash("Booking not found.", "danger"); return redirect(url_for("dashboard"))
    if session["user_id"] != b["user_id"] and session["role"] not in ("manager","admin"):
        flash("Only the requester or a manager can cancel this booking.", "danger"); return redirect(url_for("dashboard"))
    if b["status"] not in ("pending","approved","waitlisted"):
        flash("This booking can no longer be cancelled here.", "warning"); return redirect(url_for("dashboard"))
    db.execute("UPDATE bookings SET status='cancelled' WHERE id=?",(booking_id,))
    db.commit()
    log_action(session["user_id"], "BOOKING_CANCELLED", f"Booking #{booking_id}")
    flash("Booking cancelled.", "success")
    return redirect(url_for("dashboard"))

@app.route("/bookings/<int:booking_id>/incident", methods=["POST"])
@login_required
def incident(booking_id):
    db = get_db()
    b = db.execute("SELECT b.*,r.owner_id FROM bookings b JOIN resources r ON r.id=b.resource_id WHERE b.id=?",(booking_id,)).fetchone()
    if not b: flash("Booking not found.", "danger"); return redirect(url_for("dashboard"))
    if session["user_id"] not in (b["user_id"],b["owner_id"]) and session["role"] not in ("manager","admin"):
        flash("You cannot report an incident for this booking.", "danger"); return redirect(url_for("dashboard"))
    kind = request.form.get("incident_type","damage")
    description = request.form.get("description","").strip()
    if kind not in ("damage","delay","scheduling conflict","other") or not description:
        flash("Select an incident type and add a description.", "danger"); return redirect(url_for("dashboard"))
    cur = db.execute("INSERT INTO incidents(booking_id,reporter_id,incident_type,description,status,created_at) VALUES(?,?,?,?, 'open',?)",
                     (booking_id,session["user_id"],kind,description,now()))
    db.commit()
    log_action(session["user_id"], "INCIDENT_REPORTED", f"Incident #{cur.lastrowid} for booking #{booking_id}: {kind}")
    flash("Incident report submitted for review.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin")
@login_required
@roles_required("manager","admin")
def admin():
    db = get_db()
    users = db.execute("SELECT id,name,email,role,verified,created_at FROM users ORDER BY created_at DESC").fetchall()
    incidents = db.execute("""SELECT i.*,b.resource_id,r.name resource_name,u.name reporter_name FROM incidents i
      JOIN bookings b ON b.id=i.booking_id JOIN resources r ON r.id=b.resource_id JOIN users u ON u.id=i.reporter_id
      ORDER BY i.created_at DESC""").fetchall()
    logs = db.execute("""SELECT a.*,u.name actor_name FROM audit_log a LEFT JOIN users u ON u.id=a.actor_id
      ORDER BY a.id DESC LIMIT 100""").fetchall()
    return render_template("admin.html", users=users, incidents=incidents, logs=logs)

@app.route("/users/<int:user_id>/verify", methods=["POST"])
@login_required
@roles_required("manager","admin")
def verify_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
    if not user: flash("User not found.", "danger"); return redirect(url_for("admin"))
    value = 1 if request.form.get("verified") == "1" else 0
    db.execute("UPDATE users SET verified=? WHERE id=?",(value,user_id)); db.commit()
    log_action(session["user_id"], "USER_VERIFICATION_CHANGED", f"User #{user_id} verified={value}")
    flash("Verification status updated.", "success")
    return redirect(url_for("admin"))

@app.route("/incidents/<int:incident_id>/resolve", methods=["POST"])
@login_required
@roles_required("manager","admin")
def resolve_incident(incident_id):
    db = get_db()
    db.execute("UPDATE incidents SET status='resolved' WHERE id=?",(incident_id,))
    db.commit()
    log_action(session["user_id"], "INCIDENT_RESOLVED", f"Incident #{incident_id}")
    flash("Incident marked resolved.", "success")
    return redirect(url_for("admin"))

@app.route("/api/health")
def health():
    return jsonify({"status":"ok","app":"ShareSpace","time":now()})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
