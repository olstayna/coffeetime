from decimal import Decimal, InvalidOperation
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from mysql.connector import IntegrityError

from app.decorators import admin_required
from app.repositories import CouponRepository, OrderRepository, ProductRepository, UserRepository
from app.services import OrderService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _read_product_image(upload):
    extension = "." + (upload.filename or "").rsplit(".", 1)[-1].lower()
    mime_type = upload.mimetype or ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS or mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("Envie uma imagem JPG, PNG ou WebP válida.")
    image_data = upload.read()
    if not image_data:
        raise ValueError("A imagem enviada está vazia.")
    return image_data, mime_type


@admin_bp.get("")
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        products=ProductRepository.list_all(),
        orders=OrderRepository.list_all(),
        coupons=CouponRepository.list_all(),
        users=UserRepository.list_customers(),
    )


@admin_bp.post("/cupons")
@admin_required
def create_coupon():
    try:
        discount_type = request.form.get("discount_type", "")
        if discount_type not in {"percentage", "fixed"}:
            raise ValueError("Escolha um tipo de desconto válido.")
        discount_value = Decimal(request.form.get("discount_value", "0").replace(",", "."))
        minimum_amount = Decimal(request.form.get("minimum_amount", "0").replace(",", "."))
        if discount_value <= 0 or minimum_amount < 0 or (discount_type == "percentage" and discount_value > 100):
            raise ValueError("Revise os valores do cupom.")
        expires_raw = request.form.get("expires_at", "").strip()
        expires_at = datetime.strptime(expires_raw, "%Y-%m-%d").replace(hour=23, minute=59, second=59) if expires_raw else None
        code = request.form.get("code", "").strip().upper()
        if not code:
            raise ValueError("Informe o código do cupom.")
        CouponRepository.create({
            "code": code,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "minimum_amount": minimum_amount,
            "expires_at": expires_at,
            "first_order_only": "first_order_only" in request.form,
            "once_per_user": "once_per_user" in request.form,
            "active": "active" in request.form,
        })
        flash("Cupom criado com sucesso.", "success")
    except IntegrityError:
        flash("Já existe um cupom com esse código.", "error")
    except (InvalidOperation, ValueError):
        flash("Revise os dados do cupom.", "error")
    return redirect(url_for("admin.dashboard") + "#cupons")


@admin_bp.post("/cupons/<int:coupon_id>/remover")
@admin_required
def delete_coupon(coupon_id):
    CouponRepository.delete(coupon_id)
    flash("Cupom removido.", "success")
    return redirect(url_for("admin.dashboard") + "#cupons")


@admin_bp.post("/usuarios/<int:user_id>/remover")
@admin_required
def delete_user(user_id):
    if UserRepository.delete_customer(user_id):
        flash("Usuário e seus pedidos foram removidos.", "success")
    else:
        flash("Usuário não encontrado ou não pode ser removido.", "error")
    return redirect(url_for("admin.dashboard") + "#usuarios")


@admin_bp.route("/produtos/novo", methods=["GET", "POST"])
@admin_required
def new_product():
    return _product_form()


@admin_bp.route("/produtos/<int:product_id>/editar", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = ProductRepository.find(product_id)
    if not product:
        return redirect(url_for("admin.dashboard"))
    return _product_form(product)


def _product_form(product=None):
    if request.method == "POST":
        try:
            price = Decimal(request.form.get("price", "0").replace(",", "."))
            if price <= 0:
                raise InvalidOperation
            image_upload = request.files.get("image")
            image_data = image_mime = None
            if image_upload and image_upload.filename:
                image_data, image_mime = _read_product_image(image_upload)
            elif not product:
                raise ValueError("A imagem do produto é obrigatória.")
            data = {"name": request.form["name"].strip(), "description": request.form["description"].strip(),
                    "category": request.form["category"].strip(), "price": price,
                    "image_data": image_data, "image_mime": image_mime, "active": "active" in request.form}
            if not all((data["name"], data["description"], data["category"])):
                raise ValueError("Preencha todos os campos obrigatórios.")
            ProductRepository.save(data, product["id"] if product else None)
            flash("Produto salvo com sucesso.", "success")
            return redirect(url_for("admin.dashboard"))
        except ValueError as error:
            flash(str(error), "error")
        except (InvalidOperation, KeyError):
            flash("Revise os dados do produto.", "error")
    return render_template("admin/product_form.html", product=product)


@admin_bp.post("/pedidos/<int:order_id>/status")
@admin_required
def update_order_status(order_id):
    try:
        OrderService.update_status(order_id, request.form.get("status", ""))
        flash("Status atualizado.", "success")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("admin.dashboard"))
