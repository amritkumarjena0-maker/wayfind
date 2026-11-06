import sqlite3, os
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
DB = os.path.join(os.path.dirname(__file__), "wayfind.db")

SEED = [
 ("Introduction to Travel & Tourism","Fundamentals","Beginner",8,0,"Industry overview, tourism types, key stakeholders and career paths."),
 ("Tour Operations & Itinerary Design","Operations","Intermediate",12,150,"Plan, cost and run group and independent tours end to end."),
 ("Hospitality & Hotel Management","Hospitality","Intermediate",16,220,"Front office, housekeeping, F&B basics and guest experience."),
 ("Sustainable & Eco Tourism","Sustainability","Intermediate",10,120,"Responsible travel, community tourism and conservation economics."),
 ("Airline Ticketing & GDS Systems","Operations","Beginner",6,90,"Fares, reservations and airline codes using GDS workflows."),
 ("Digital Marketing for Tourism","Marketing","Intermediate",8,130,"SEO, social media and content strategy for destinations and agencies."),
 ("Destination Management","Management","Advanced",20,300,"Branding, policy and stakeholder planning for destinations."),
 ("Cultural Heritage Tourism","Fundamentals","Beginner",6,60,"Interpret heritage sites, museums and living culture for visitors."),
 ("Event & MICE Management","Hospitality","Advanced",14,260,"Meetings, incentives, conferences and exhibitions planning."),
 ("Tourism Law & Risk Management","Management","Advanced",10,180,"Contracts, liability, safety and crisis response in travel."),
 ("Travel Photography & Storytelling","Marketing","Beginner",5,0,"Shoot and write compelling travel content for portfolios and brands."),
 ("Adventure Tourism Guiding","Operations","Intermediate",12,170,"Guiding skills, safety protocols and first aid for outdoor trips."),
]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
        level TEXT NOT NULL, weeks INTEGER NOT NULL, fee INTEGER NOT NULL, description TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS enquiries(
        id INTEGER PRIMARY KEY, course_id INTEGER REFERENCES courses(id),
        name TEXT NOT NULL, email TEXT NOT NULL, message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    if con.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        con.executemany("INSERT INTO courses(title,category,level,weeks,fee,description) VALUES(?,?,?,?,?,?)", SEED)
    con.commit(); con.close()

SORTS = {"title": "title", "weeks": "weeks", "fee": "fee"}

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "")
    lvl = request.args.get("level", "")
    sort = SORTS.get(request.args.get("sort", "title"), "title")
    sql, args = "SELECT * FROM courses WHERE 1=1", []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
        args += [f"%{q}%"] * 3
    if cat: sql += " AND category=?"; args.append(cat)
    if lvl: sql += " AND level=?"; args.append(lvl)
    sql += f" ORDER BY {sort}"
    courses = db().execute(sql, args).fetchall()
    cats = [r[0] for r in db().execute("SELECT DISTINCT category FROM courses ORDER BY 1")]
    return render_template("index.html", courses=courses, cats=cats, q=q, cat=cat, lvl=lvl,
                           sort=request.args.get("sort", "title"), saved=session.get("saved", []))

@app.route("/course/<int:cid>")
def course(cid):
    c = db().execute("SELECT * FROM courses WHERE id=?", (cid,)).fetchone() or abort(404)
    return render_template("course.html", c=c, saved=cid in session.get("saved", []))

@app.post("/save/<int:cid>")
def save(cid):
    s = set(session.get("saved", []))
    s.symmetric_difference_update({cid})
    session["saved"] = sorted(s)
    return redirect(request.referrer or url_for("index"))

@app.route("/shortlist")
def shortlist():
    ids = session.get("saved", [])
    rows = []
    if ids:
        rows = db().execute(f"SELECT * FROM courses WHERE id IN ({','.join('?'*len(ids))})", ids).fetchall()
    return render_template("shortlist.html", courses=rows)

@app.post("/enquire/<int:cid>")
def enquire(cid):
    name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip()
    if not name or "@" not in email:
        flash("Please enter a name and a valid email.", "error")
    else:
        db().execute("INSERT INTO enquiries(course_id,name,email,message) VALUES(?,?,?,?)",
                     (cid, name, email, request.form.get("message", "").strip()))
        db().commit()
        flash("Enquiry sent. We'll be in touch.", "ok")
    return redirect(url_for("course", cid=cid))

@app.route("/admin/enquiries")
def admin_enquiries():  # TODO: add login before deploying
    rows = db().execute("""SELECT e.*, c.title FROM enquiries e
                           JOIN courses c ON c.id=e.course_id ORDER BY e.id DESC""").fetchall()
    return render_template("admin.html", rows=rows)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
