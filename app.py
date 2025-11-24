from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# -------------------------------------------------------
# KONFIGURACJA
# -------------------------------------------------------

DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "climbwall")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# sekretny klucz do sesji (cookie)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

# Folder na uploadowane zdjęcia
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# -------------------------------------------------------
# MODELE BAZY DANYCH
# -------------------------------------------------------

class Route(db.Model):
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # "boulder" / "lina"
    sector = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    created_by = db.Column(db.Integer)  # na później, jak podepniemy users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Route {self.name} ({self.grade})>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")  # "user" / "admin"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# -------------------------------------------------------
# INICJALIZACJA BAZY – tabele + przykładowe dane + domyślny admin
# -------------------------------------------------------

def init_db():
    """Tworzy tabele i wrzuca przykładowe dane, jeśli baza jest pusta.
       Dodaje też domyślnego admina, jeśli go nie ma.
    """
    db.create_all()

    # przykładowe drogi
    if Route.query.count() == 0:
        sample_routes = [
            Route(
                name="Yellow Arete",
                grade="6b",
                type="boulder",
                sector="Sector A",
                description="Krótki, siłowy boulder na krawądkach.",
                image_path="/static/images/sample1.jpg",
                video_url="https://youtu.be/example1",
            ),
            Route(
                name="Blue Line",
                grade="5c",
                type="lina",
                sector="Sector B",
                description="Dłuższa droga na linę, techniczna.",
                image_path="/static/images/sample2.jpg",
                video_url="",
            ),
        ]
        db.session.add_all(sample_routes)
        db.session.commit()
        print("🔹 Dodano przykładowe drogi do bazy.")

    # domyślny admin
    admin_email = "admin@climbwall.local"
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            email=admin_email,
            password_hash=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin_user)
        db.session.commit()
        print("🔹 Utworzono użytkownika admin:")
        print("    email: admin@climbwall.local")
        print("    hasło: admin123")


with app.app_context():
    init_db()


# -------------------------------------------------------
# POMOCNICZE: kontekst + dekorator admin_required
# -------------------------------------------------------

@app.context_processor
def inject_user():
    """Umożliwia użycie current_user_* w szablonach."""
    return dict(
        current_user_email=session.get("user_email"),
        current_user_role=session.get("user_role"),
    )


def admin_required(f):
    """Dekorator – wymaga zalogowanego admina."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("user_role") != "admin":
            flash("Musisz być zalogowany jako administrator.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# -------------------------------------------------------
# WIDOKI PUBLICZNE
# -------------------------------------------------------

@app.route("/")
def index():
    featured = Route.query.limit(2).all()
    return render_template("index.html", featured_routes=featured)


@app.route("/routes")
def routes():
    all_routes = Route.query.all()
    return render_template("routes.html", routes=all_routes)

@app.route("/routes/<int:route_id>")
def route_detail(route_id):
    route = Route.query.get_or_404(route_id)
    return render_template("route_detail.html", route=route)

# -------------------------------------------------------
# LOGOWANIE / WYLOGOWANIE / (opcjonalnie rejestracja)
# -------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Nieprawidłowy e-mail lub hasło.", "error")
            return render_template("login.html")

        # logowanie OK – zapisujemy info w sesji
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_role"] = user.role

        flash("Zalogowano pomyślnie.", "success")

        # jak admin – leć do panelu, jak zwykły user – na stronę główną
        if user.role == "admin":
            return redirect(url_for("admin"))
        else:
            return redirect(url_for("index"))

    # GET – pokaż formularz logowania
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Zostałeś wylogowany.", "success")
    return redirect(url_for("index"))


# (opcjonalnie) rejestracja zwykłego użytkownika – jeśli będzie potrzebna
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Podaj e-mail i hasło.", "error")
            return render_template("register.html")

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Użytkownik o takim e-mailu już istnieje.", "error")
            return render_template("register.html")

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role="user"
        )
        db.session.add(user)
        db.session.commit()

        flash("Konto utworzone. Możesz się zalogować.", "success")
        return redirect(url_for("login"))

    # jak nie chcesz rejestracji – możesz tej trasy w ogóle nie używać
    return render_template("register.html")
    # UWAGA: na razie nie tworzymy register.html, więc jeśli nie używasz
    # tej funkcji, możesz ją spokojnie skasować albo zakomentować.


# -------------------------------------------------------
# PANEL ADMINA (chroniony)
# -------------------------------------------------------

@app.route("/admin")
@admin_required
def admin():
    all_routes = Route.query.all()
    return render_template("admin.html", routes=all_routes, route_to_edit=None)


@app.route("/admin/add", methods=["POST"])
@admin_required
def add_route():
    name = request.form.get("name", "").strip()
    grade = request.form.get("grade", "").strip()
    type_ = request.form.get("type", "").strip()
    sector = request.form.get("sector", "").strip()
    description = request.form.get("description", "").strip()
    video_url = request.form.get("video_url", "").strip()

    image_file = request.files.get("image")
    image_path = None

    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        name_part, ext = os.path.splitext(filename)
        filename = f"{name_part}_{timestamp}{ext}"

        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(save_path)

        image_path = "/static/uploads/" + filename

    new_route = Route(
        name=name,
        grade=grade,
        type=type_,
        sector=sector,
        description=description,
        image_path=image_path,
        video_url=video_url,
        created_by=session.get("user_id"),
    )

    db.session.add(new_route)
    db.session.commit()

    try:
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()} ADDED route: {name} by {session.get('user_email')}\n")
    except Exception as e:
        print("Błąd zapisu do logs.txt:", e)

    return redirect(url_for("admin"))


@app.route("/admin/edit/<int:route_id>", methods=["GET"])
@admin_required
def edit_route(route_id):
    all_routes = Route.query.all()
    route_to_edit = Route.query.get_or_404(route_id)
    return render_template("admin.html", routes=all_routes, route_to_edit=route_to_edit)


@app.route("/admin/edit/<int:route_id>", methods=["POST"])
@admin_required
def update_route(route_id):
    route = Route.query.get_or_404(route_id)

    route.name = request.form.get("name", "").strip()
    route.grade = request.form.get("grade", "").strip()
    route.type = request.form.get("type", "").strip()
    route.sector = request.form.get("sector", "").strip()
    route.description = request.form.get("description", "").strip()
    route.video_url = request.form.get("video_url", "").strip()

    image_file = request.files.get("image")

    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        name_part, ext = os.path.splitext(filename)
        filename = f"{name_part}_{timestamp}{ext}"

        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(save_path)

        if route.image_path and route.image_path.startswith("/static/uploads/"):
            old_path = route.image_path.lstrip("/")
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception as e:
                print("Nie udało się usunąć starego zdjęcia:", e)

        route.image_path = "/static/uploads/" + filename

    db.session.commit()

    try:
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()} UPDATED route: {route.id} {route.name} by {session.get('user_email')}\n")
    except Exception as e:
        print("Błąd zapisu do logs.txt:", e)

    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:route_id>", methods=["POST"])
@admin_required
def delete_route(route_id):
    route = Route.query.get_or_404(route_id)

    if route.image_path and route.image_path.startswith("/static/uploads/"):
        old_path = route.image_path.lstrip("/")
        try:
            if os.path.exists(old_path):
                os.remove(old_path)
        except Exception as e:
            print("Nie udało się usunąć zdjęcia przy delete:", e)

    name_for_log = route.name

    db.session.delete(route)
    db.session.commit()

    try:
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()} DELETED route: {route_id} {name_for_log} by {session.get('user_email')}\n")
    except Exception as e:
        print("Błąd zapisu do logs.txt:", e)

    return redirect(url_for("admin"))


# -------------------------------------------------------
# START APLIKACJI
# -------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
