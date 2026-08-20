from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for

from app.decorators import login_required
from app.repositories import OrderRepository, ProductRepository
from app.services import CartService, OrderService

shop_bp = Blueprint("shop", __name__)


def cart_ajax_response(message):
    summary = CartService.summary()
    count = sum(item["quantity"] for item in summary["items"])
    return jsonify(
        ok=True,
        message=message,
        count=count,
        preview_html=render_template(
            "shared/_cart_preview.html",
            cart_preview=summary,
            cart_count=count,
        ),
    )


@shop_bp.get("/")
def catalog():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    products = ProductRepository.list_active(search, category)
    categories = sorted({p["category"] for p in ProductRepository.list_active()})
    featured = products[0] if products else None
    return render_template("shop/catalog.html", products=products, categories=categories, search=search, selected_category=category, featured=featured)


@shop_bp.get("/produto/<int:product_id>")
def product_detail(product_id):
    product = ProductRepository.find(product_id, active_only=True)
    if not product:
        abort(404)
    recommendations = ProductRepository.recommendations(product_id, limit=4)
    return render_template("shop/product.html", product=product, recommendations=recommendations)


@shop_bp.post("/carrinho/adicionar/<int:product_id>")
def add_to_cart(product_id):
    try:
        quantity = int(request.form.get("quantity", 1))
        if quantity < 1 or quantity > 99:
            raise ValueError("Quantidade inválida.")
        CartService.add(product_id, quantity)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            label = "item adicionado" if quantity == 1 else "itens adicionados"
            return cart_ajax_response(f"{quantity} {label} ao carrinho.")
        flash("Produto adicionado ao carrinho.", "success")
    except (ValueError, TypeError):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=False, message="Não foi possível adicionar este produto."), 400
        flash("Não foi possível adicionar este produto.", "error")
    return redirect(request.referrer or url_for("shop.catalog"))


@shop_bp.route("/carrinho", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        try:
            CartService.update(int(request.form["product_id"]), int(request.form["quantity"]))
        except (ValueError, KeyError):
            flash("Quantidade inválida.", "error")
        return redirect(url_for("shop.cart"))
    summary = CartService.summary()
    return render_template("shop/cart.html", **summary)


@shop_bp.post("/carrinho/ajustar/<int:product_id>")
def adjust_cart(product_id):
    current = session.get("cart", {}).get(str(product_id), 0)
    try:
        delta = int(request.form.get("delta", 0))
        CartService.update(product_id, current + delta)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return cart_ajax_response("Carrinho atualizado.")
    except ValueError:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=False, message="Não foi possível alterar a quantidade."), 400
        flash("Não foi possível alterar a quantidade.", "error")
    return redirect(url_for("shop.cart"))


@shop_bp.post("/carrinho/cupom")
def apply_coupon():
    try:
        coupon = CartService.apply_coupon(request.form.get("coupon", ""))
        flash(f"Cupom {coupon['code']} aplicado!", "success")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("shop.cart"))


@shop_bp.post("/carrinho/cupom/remover")
def remove_coupon():
    session.pop("coupon_code", None)
    flash("Cupom removido.", "success")
    return redirect(url_for("shop.cart"))


@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    summary = CartService.summary()
    items, total = summary["items"], summary["total"]
    if not items:
        flash("Adicione produtos antes de finalizar.", "warning")
        return redirect(url_for("shop.catalog"))
    if request.method == "POST":
        try:
            order_id = OrderService.create(session["user_id"], request.form)
            flash(f"Pedido #{order_id} recebido com sucesso!", "success")
            return redirect(url_for("shop.order_detail", order_id=order_id))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("shop/checkout.html", **summary)


@shop_bp.get("/pedidos")
@login_required
def orders():
    return render_template("shop/orders.html", orders=OrderRepository.list_for_user(session["user_id"]))


@shop_bp.get("/pedidos/<int:order_id>")
@login_required
def order_detail(order_id):
    order = OrderRepository.find_for_user(order_id, session["user_id"])
    if not order:
        abort(404)
    return render_template("shop/order_detail.html", order=order)
