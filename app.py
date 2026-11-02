import os, time, socket
import psycopg2
from flask import Flask, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Trust the X-Forwarded-* headers added by proxies such as the Cloudflare tunnel
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


def q(sql, args=(), fetch=False):
    conn = psycopg2.connect(host=os.environ.get("DB_HOST", "db"),
                            dbname=os.environ.get("DB_NAME", "notes"),
                            user=os.environ.get("DB_USER", "notes"),
                            password=os.environ.get("DB_PASSWORD", "notespass"))
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()


def init_db():
    for _ in range(30):
        try:
            q("""CREATE TABLE IF NOT EXISTS users (
                   id SERIAL PRIMARY KEY,
                   username TEXT UNIQUE NOT NULL,
                   password_hash TEXT NOT NULL);
                 CREATE TABLE IF NOT EXISTS notes (
                   id SERIAL PRIMARY KEY,
                   user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                   body TEXT NOT NULL,
                   created TIMESTAMP DEFAULT now());""")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise SystemExit("Database not reachable")


init_db()


@app.context_processor
def inject():
    return {"host": socket.gethostname(), "user": session.get("username")}


@app.route("/")
def index():
    if "uid" not in session:
        return redirect(url_for("login"))
    rows = q("SELECT id, body, created FROM notes WHERE user_id=%s ORDER BY id DESC",
             (session["uid"],), fetch=True)
    return render_template("notes.html", notes=rows)


@app.route("/add", methods=["POST"])
def add():
    body = request.form.get("body", "").strip()
    if "uid" in session and body:
        q("INSERT INTO notes (user_id, body) VALUES (%s, %s)", (session["uid"], body))
    return redirect(url_for("index"))


@app.route("/delete/<int:nid>", methods=["POST"])
def delete(nid):
    if "uid" in session:
        q("DELETE FROM notes WHERE id=%s AND user_id=%s", (nid, session["uid"]))
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("username", "").strip()
        pw = request.form.get("password", "")
        if len(name) < 3 or len(pw) < 6:
            flash("Username needs 3+ characters and password 6+.")
        elif q("SELECT 1 FROM users WHERE username=%s", (name,), fetch=True):
            flash("That username is taken.")
        else:
            q("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
              (name, generate_password_hash(pw)))
            flash("Account created. Please log in.")
            return redirect(url_for("login"))
    return render_template("auth.html", title="Register", button="Create account",
                           alt_url=url_for("login"), alt_text="Already have an account? Log in")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        row = q("SELECT id, password_hash FROM users WHERE username=%s",
                (request.form.get("username", "").strip(),), fetch=True)
        if row and check_password_hash(row[0][1], request.form.get("password", "")):
            session["uid"], session["username"] = row[0][0], request.form["username"].strip()
            return redirect(url_for("index"))
        flash("Wrong username or password.")
    return render_template("auth.html", title="Log in", button="Log in",
                           alt_url=url_for("register"), alt_text="No account yet? Register")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
