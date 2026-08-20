import re
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.decorators import login_required
from app.repositories import UserRepository

auth_bp = Blueprint("auth", __name__)


def safe_next_url(target):
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return None
    return target


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    next_url = safe_next_url(request.values.get("next"))
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
                return redirect(url_for("auth.login", next=next_url) if next_url else url_for("auth.login"))
            except IntegrityError:
                flash("Este e-mail já está cadastrado.", "error")
    return render_template("auth/register.html", next_url=next_url)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = safe_next_url(request.values.get("next"))
    if request.method == "POST":
        user = UserRepository.find_by_email(request.form.get("email", "").strip().lower())
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            cart = session.get("cart", {}).copy()
            coupon_code = session.get("coupon_code")
            pending_coupon_code = session.get("pending_coupon_code")
            session.clear()
            session.update(user_id=user["id"], user_name=user["name"], role=user["role"])
            if user["role"] != "admin" and cart:
                session["cart"] = cart
            if user["role"] != "admin" and coupon_code:
                session["coupon_code"] = coupon_code
            if user["role"] != "admin" and pending_coupon_code:
                session["pending_coupon_code"] = pending_coupon_code
            if user["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(next_url or url_for("shop.catalog"))
        flash("E-mail ou senha inválidos.", "error")
    return render_template("auth/login.html", next_url=next_url)
@auth_bp.route("/minha-conta", methods=["GET", "POST"])
@login_required
def account():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    user = UserRepository.find(session["user_id"])
    if not user:
        session.clear()
        flash("Não foi possível localizar sua conta.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        intent = request.form.get("intent")
        if intent == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            password_confirmation = request.form.get("password_confirmation", "")
            if not check_password_hash(user["password_hash"], current_password):
                flash("A senha atual está incorreta.", "error")
            elif len(new_password) < 8 or not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
                flash("A nova senha deve ter ao menos 8 caracteres, com letras e números.", "error")
            elif new_password != password_confirmation:
                flash("A confirmação da nova senha não confere.", "error")
            else:
                UserRepository.update_password(session["user_id"], generate_password_hash(new_password))
                flash("Senha alterada com sucesso.", "success")
                return redirect(url_for("auth.account"))
        else:
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            if not all((email, phone)):
                flash("Preencha todos os campos.", "error")
            elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                flash("Informe um e-mail válido.", "error")
            elif not re.fullmatch(r"\(\d{2}\) \d{5}-\d{4}", phone):
                flash("Informe o celular no formato (00) 91234-5678.", "error")
            else:
                try:
                    UserRepository.update_profile(session["user_id"], email, phone)
                    flash("Dados atualizados com sucesso.", "success")
                    return redirect(url_for("auth.account"))
                except IntegrityError:
                    flash("Este e-mail já está cadastrado em outra conta.", "error")
            user = {**user, "email": email, "phone": phone}

    return render_template("auth/account.html", user=user, account_section="profile")


@auth_bp.post("/sair")
def logout():
    session.clear()
    return redirect(url_for("shop.catalog"))
