import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.repositories import UserRepository

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower()
        password, phone = request.form.get("password", ""), request.form.get("phone", "").strip()
        if not all((name, email, password, phone)):
            flash("Preencha todos os campos.", "error")
        elif not re.fullmatch(r"\(\d{2}\) \d{5}-\d{4}", phone):
            flash("Informe o celular no formato (00) 91234-5678.", "error")
        elif len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            flash("A senha deve ter ao menos 8 caracteres, com letras e números.", "error")
        else:
            try:
                UserRepository.create(name, email, generate_password_hash(password), phone)
                flash("Conta criada. Agora você já pode entrar.", "success")
                return redirect(url_for("auth.login"))
            except IntegrityError:
                flash("Este e-mail já está cadastrado.", "error")
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = UserRepository.find_by_email(request.form.get("email", "").strip().lower())
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session.update(user_id=user["id"], user_name=user["name"], role=user["role"])
            return redirect(url_for("admin.dashboard" if user["role"] == "admin" else "shop.catalog"))
        flash("E-mail ou senha inválidos.", "error")
    return render_template("auth/login.html")


@auth_bp.post("/sair")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "success")
    return redirect(url_for("shop.catalog"))
