from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from celery import Celery
from datetime import datetime, timedelta
import google.oauth2.credentials
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "chave_secreta"
CORS(app)

# Configuração do banco de dados
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://tarefas:yB6Ypyy2LZGDpRa6@191.252.100.132:3306/tarefas"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configuração do Celery
app.config["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
app.config["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"

db = SQLAlchemy(app)
celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"])
celery.conf.update(app.config)

# Modelos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    tasks = db.relationship('Task', backref='user', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500))
    date_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='não iniciado')
    google_event_id = db.Column(db.String(150), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Rotas
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login_user")
    return redirect("/tasks")

@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    if "user_id" not in session:
        return redirect("/login_user")

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        date_time = datetime.strptime(request.form["date_time"], "%Y-%m-%dT%H:%M")
        status = request.form.get("status", "não iniciado")

        new_task = Task(title=title, description=description, date_time=date_time,
                        status=status, user=user)
        db.session.add(new_task)
        db.session.commit()
        
        return redirect("/tasks")

    filtro = request.args.get('filter', 'all')
    query = Task.query.filter_by(user_id=user.id)
    if filtro != 'all':
        query = query.filter_by(status=filtro)
    tasks = query.order_by(Task.date_time).all()
    return render_template("index.html", tasks=tasks)

@app.route("/task/<int:task_id>/update_status", methods=["POST"])
def update_status(task_id):
    task = Task.query.get(task_id)
    if task and task.user_id == session.get("user_id"):
        new_status = request.form["status"]
        task.status = new_status
        db.session.commit()
        flash("Status atualizado!")
    return redirect("/tasks")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        if User.query.filter_by(username=username).first():
            flash("Nome de usuário já existe.")
            return redirect("/register")
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Cadastro realizado com sucesso! Faça login.")
        return redirect("/login_user")
    return render_template("register.html")

@app.route("/login_user", methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Login realizado com sucesso!")
            return redirect("/tasks")
        else:
            flash("Credenciais inválidas.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Você saiu da conta.")
    return redirect("/login_user")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=3000)
