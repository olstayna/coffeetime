import re
from decimal import Decimal

from flask import session

from app.database import execute, get_db
from app.repositories import CouponRepository, OrderRepository, ProductRepository


class CartService:
    @staticmethod
    def add(product_id, quantity=1):
        product = ProductRepository.find(product_id, active_only=True)
        if not product:
            raise ValueError("Produto indisponível.")
        cart = session.get("cart", {})
        key = str(product_id)
        cart[key] = cart.get(key, 0) + max(1, quantity)
        session["cart"] = cart

    @staticmethod
    def update(product_id, quantity):
        cart = session.get("cart", {})
        key = str(product_id)
        if quantity <= 0:
            cart.pop(key, None)
        elif ProductRepository.find(product_id, active_only=True):
            cart[key] = min(quantity, 99)
        session["cart"] = cart

    @staticmethod
    def details():
        items, total = [], Decimal("0.00")
        for product_id, quantity in session.get("cart", {}).items():
            product = ProductRepository.find(product_id, active_only=True)
            if product:
                subtotal = product["price"] * quantity
                items.append({"product": product, "quantity": quantity, "subtotal": subtotal})
                total += subtotal
        return items, total

    @staticmethod
    def summary():
        items, subtotal = CartService.details()
        coupon = None
        discount = Decimal("0.00")
        code = session.get("coupon_code")

        if code:
            coupon = CouponRepository.find_valid(code)
            if coupon and coupon.get("first_order_only"):
                user_id = session.get("user_id")
                if not user_id or OrderRepository.has_orders_for_user(user_id):
                    session.pop("coupon_code", None)
                    coupon = None
            if coupon and coupon.get("once_per_user"):
                user_id = session.get("user_id")
                if not user_id or OrderRepository.has_used_coupon(user_id, coupon["code"]):
                    session.pop("coupon_code", None)
                    coupon = None
            if coupon and subtotal >= coupon["minimum_amount"]:
                if coupon["discount_type"] == "percentage":
                    discount = subtotal * coupon["discount_value"] / Decimal("100")
                else:
                    discount = coupon["discount_value"]
                discount = min(discount, subtotal).quantize(Decimal("0.01"))
            else:
                session.pop("coupon_code", None)
                coupon = None

        return {
            "items": items,
            "subtotal": subtotal,
            "coupon": coupon,
            "discount": discount,
            "total": subtotal - discount,
        }

    @staticmethod
    def apply_coupon(code):
        coupon = CouponRepository.find_valid(code.strip())
        _, subtotal = CartService.details()
        if not coupon:
            raise ValueError("Cupom inválido ou expirado.")
        if coupon.get("first_order_only"):
            user_id = session.get("user_id")
            if not user_id:
                session["pending_coupon_code"] = coupon["code"]
                raise ValueError("Entre na sua conta para usar este cupom de primeira compra.")
            if OrderRepository.has_orders_for_user(user_id):
                raise ValueError("Este cupom é válido somente na primeira compra.")
        if coupon.get("once_per_user"):
            user_id = session.get("user_id")
            if not user_id:
                session["pending_coupon_code"] = coupon["code"]
                raise ValueError("Entre na sua conta para usar este cupom de uso único.")
            if OrderRepository.has_used_coupon(user_id, coupon["code"]):
                raise ValueError("Este cupom já foi utilizado por você.")
        if subtotal < coupon["minimum_amount"]:
            minimum = str(coupon["minimum_amount"]).replace(".", ",")
            raise ValueError(f"Este cupom exige um pedido mínimo de R$ {minimum}.")
        session["coupon_code"] = coupon["code"]
        return coupon


class OrderService:
    VALID_PAYMENTS = {"pix", "cartao", "dinheiro"}
    STATUS_FLOW = ["recebido", "em preparo", "em rota", "entregue"]

    @classmethod
    def create(cls, user_id, form):
        summary = CartService.summary()
        items, total = summary["items"], summary["total"]
        required = ["street", "number", "district", "city", "postal_code", "payment_method"]
        if not items:
            raise ValueError("O carrinho está vazio.")
        if any(not form.get(field, "").strip() for field in required):
            raise ValueError("Preencha todos os dados de entrega e pagamento.")
        if not re.fullmatch(r"\d{5}-\d{3}", form["postal_code"].strip()):
            raise ValueError("Informe o CEP no formato 00000-000.")
        if form["payment_method"] not in cls.VALID_PAYMENTS:
            raise ValueError("Forma de pagamento inválida.")
        if summary["coupon"] and summary["coupon"].get("first_order_only") and OrderRepository.has_orders_for_user(user_id):
            session.pop("coupon_code", None)
            raise ValueError("Este cupom é válido somente na primeira compra.")
        if summary["coupon"] and summary["coupon"].get("once_per_user") and OrderRepository.has_used_coupon(user_id, summary["coupon"]["code"]):
            session.pop("coupon_code", None)
            raise ValueError("Este cupom já foi utilizado por você.")

        db = get_db()
        try:
            order_id = execute(
                "INSERT INTO orders (user_id,total,status,payment_method,street,number,district,city,postal_code,notes,coupon_code,discount) VALUES (%s,%s,'recebido',%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (user_id, total, form["payment_method"], form["street"], form["number"], form["district"], form["city"], form["postal_code"], form.get("notes", ""), summary["coupon"]["code"] if summary["coupon"] else None, summary["discount"]), commit=False,
            )
            for item in items:
                execute("INSERT INTO order_items (order_id,product_id,product_name,unit_price,quantity,subtotal) VALUES (%s,%s,%s,%s,%s,%s)",
                        (order_id, item["product"]["id"], item["product"]["name"], item["product"]["price"], item["quantity"], item["subtotal"]), commit=False)
            execute("INSERT INTO order_status_history (order_id,status) VALUES (%s,'recebido')", (order_id,), commit=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
        session.pop("cart", None)
        session.pop("coupon_code", None)
        return order_id

    @classmethod
    def update_status(cls, order_id, new_status):
        from app.database import fetch_one
        order = fetch_one("SELECT status FROM orders WHERE id=%s", (order_id,))
        if not order or new_status not in cls.STATUS_FLOW:
            raise ValueError("Pedido ou status inválido.")
        current_index = cls.STATUS_FLOW.index(order["status"])
        new_index = cls.STATUS_FLOW.index(new_status)
        if new_index != current_index + 1:
            raise ValueError("O pedido deve seguir a ordem normal de atendimento.")
        execute("UPDATE orders SET status=%s WHERE id=%s", (new_status, order_id))
        execute("INSERT INTO order_status_history (order_id,status) VALUES (%s,%s)", (order_id, new_status))
