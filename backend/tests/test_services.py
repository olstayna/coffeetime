import unittest
from decimal import Decimal
from urllib.parse import urlsplit
from unittest.mock import patch

from flask import Flask, session
from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app
from app.services import CartService, OrderService


class CartServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "test"
        self.context = self.app.test_request_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    @patch("app.services.ProductRepository.find")
    def test_add_same_product_increases_quantity(self, find):
        find.return_value = {"id": 1, "name": "Espresso", "price": Decimal("7.00")}

        CartService.add(1)
        CartService.add(1, 2)

        self.assertEqual(session["cart"]["1"], 3)

    @patch("app.services.ProductRepository.find")
    def test_zero_quantity_removes_product(self, find):
        find.return_value = {"id": 1}
        session["cart"] = {"1": 2}

        CartService.update(1, 0)

        self.assertNotIn("1", session["cart"])

    @patch("app.services.ProductRepository.find")
    def test_cart_calculates_total(self, find):
        find.return_value = {"id": 1, "name": "Espresso", "price": Decimal("7.00")}
        session["cart"] = {"1": 3}

        items, total = CartService.details()

        self.assertEqual(items[0]["subtotal"], Decimal("21.00"))
        self.assertEqual(total, Decimal("21.00"))

    @patch("app.services.OrderRepository.has_orders_for_user", return_value=True)
    @patch("app.services.CartService.details", return_value=([], Decimal("40.00")))
    @patch("app.services.CouponRepository.find_valid")
    def test_first_order_coupon_rejects_returning_customer(self, find_coupon, _details, _has_orders):
        find_coupon.return_value = {
            "code": "BEMVINDO10", "first_order_only": True, "minimum_amount": Decimal("20.00")
        }
        session["user_id"] = 10

        with self.assertRaisesRegex(ValueError, "somente na primeira compra"):
            CartService.apply_coupon("BEMVINDO10")

    @patch("app.services.OrderRepository.has_orders_for_user", return_value=False)
    @patch("app.services.CartService.details", return_value=([], Decimal("40.00")))
    @patch("app.services.CouponRepository.find_valid")
    def test_first_order_coupon_accepts_new_customer(self, find_coupon, _details, _has_orders):
        find_coupon.return_value = {
            "code": "BEMVINDO10", "first_order_only": True, "minimum_amount": Decimal("20.00")
        }
        session["user_id"] = 10

        CartService.apply_coupon("BEMVINDO10")

        self.assertEqual(session["coupon_code"], "BEMVINDO10")

    @patch("app.services.CartService.details", return_value=([], Decimal("40.00")))
    @patch("app.services.CouponRepository.find_valid")
    def test_first_order_coupon_is_saved_as_pending_for_guest(self, find_coupon, _details):
        find_coupon.return_value = {
            "code": "BEMVINDO10",
            "first_order_only": True,
            "minimum_amount": Decimal("20.00"),
        }

        with self.assertRaisesRegex(ValueError, "Entre na sua conta"):
            CartService.apply_coupon("BEMVINDO10")

        self.assertEqual(session["pending_coupon_code"], "BEMVINDO10")

    @patch("app.services.OrderRepository.has_used_coupon", return_value=True)
    @patch("app.services.CartService.details", return_value=([], Decimal("40.00")))
    @patch("app.services.CouponRepository.find_valid")
    def test_once_per_user_coupon_rejects_second_use(self, find_coupon, _details, _has_used):
        find_coupon.return_value = {
            "code": "CLIENTE10",
            "first_order_only": False,
            "once_per_user": True,
            "minimum_amount": Decimal("20.00"),
        }
        session["user_id"] = 10

        with self.assertRaisesRegex(ValueError, "já foi utilizado"):
            CartService.apply_coupon("CLIENTE10")

    @patch("app.services.OrderRepository.has_used_coupon", return_value=False)
    @patch("app.services.OrderRepository.has_orders_for_user", return_value=True)
    @patch("app.services.CartService.details", return_value=([], Decimal("40.00")))
    @patch("app.services.CouponRepository.find_valid")
    def test_once_per_user_coupon_accepts_returning_customer(
        self, find_coupon, _details, _has_orders, _has_used
    ):
        find_coupon.return_value = {
            "code": "CLIENTE10",
            "first_order_only": False,
            "once_per_user": True,
            "minimum_amount": Decimal("20.00"),
        }
        session["user_id"] = 10

        CartService.apply_coupon("CLIENTE10")

        self.assertEqual(session["coupon_code"], "CLIENTE10")


class OrderServiceTest(unittest.TestCase):
    def test_status_flow_has_expected_order(self):
        self.assertEqual(
            OrderService.STATUS_FLOW,
            ["recebido", "em preparo", "em rota", "entregue"],
        )

    def test_payment_options_are_limited(self):
        self.assertEqual(OrderService.VALID_PAYMENTS, {"pix", "cartao", "dinheiro"})

    @patch("app.services.CartService.summary")
    def test_checkout_rejects_invalid_postal_code(self, summary):
        summary.return_value = {"items": [{"product": {"id": 1}}], "total": Decimal("10.00"), "coupon": None}
        form = {"street": "Rua A", "number": "10", "district": "Centro", "city": "Cidade", "postal_code": "abc123", "payment_method": "pix"}

        with self.assertRaisesRegex(ValueError, "CEP"):
            OrderService.create(1, form)


class CartAjaxTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = self.app.test_client()
        self.product = {
            "id": 1,
            "name": "Espresso",
            "price": Decimal("7.00"),
            "image_data": None,
            "image_mime": None,
        }

    @patch("app.services.ProductRepository.find")
    def test_add_ajax_returns_updated_preview(self, find):
        find.return_value = self.product

        response = self.client.post(
            "/carrinho/adicionar/1",
            data={"quantity": "2"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["count"], 2)
        self.assertIn("Espresso", data["preview_html"])
        self.assertIn("js-cart-adjust", data["preview_html"])

    @patch("app.services.ProductRepository.find")
    def test_adjust_ajax_removes_last_item_from_preview(self, find):
        find.return_value = self.product
        with self.client.session_transaction() as cart_session:
            cart_session["cart"] = {"1": 1}

        response = self.client.post(
            "/carrinho/ajustar/1",
            data={"delta": "-1"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["count"], 0)
        self.assertIn("Seu carrinho está vazio", data["preview_html"])

    @patch("app.routes.shop.CartService.apply_coupon")
    @patch("app.routes.shop.CartService.summary")
    def test_checkout_coupon_ajax_returns_recalculated_summary(self, summary, apply_coupon):
        coupon = {
            "code": "BEMVINDO10",
            "discount_type": "percentage",
            "discount_value": Decimal("10.00"),
        }
        apply_coupon.return_value = coupon
        summary.return_value = {
            "items": [{"product": self.product, "quantity": 2, "subtotal": Decimal("14.00")}],
            "subtotal": Decimal("14.00"),
            "coupon": coupon,
            "discount": Decimal("1.40"),
            "total": Decimal("12.60"),
        }

        response = self.client.post(
            "/carrinho/cupom",
            data={"coupon": "BEMVINDO10", "return_to": "checkout"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Cupom BEMVINDO10", data["summary_html"])
        self.assertIn("12,60", data["summary_html"])

    @patch("app.routes.shop.CartService.summary")
    def test_checkout_displays_coupon_input(self, summary):
        summary.return_value = {
            "items": [{"product": self.product, "quantity": 1, "subtotal": Decimal("7.00")}],
            "subtotal": Decimal("7.00"),
            "coupon": None,
            "discount": Decimal("0.00"),
            "total": Decimal("7.00"),
        }
        with self.client.session_transaction() as logged_session:
            logged_session.update(user_id=7, user_name="Cliente", role="customer")

        response = self.client.get("/checkout")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="checkout-coupon"', response.data)
        self.assertIn(b'form="checkout-form"', response.data)

    @patch("app.routes.shop.CartService.apply_coupon")
    @patch("app.routes.shop.CartService.summary")
    def test_checkout_automatically_applies_pending_coupon(self, summary, apply_coupon):
        apply_coupon.return_value = {"code": "BEMVINDO10"}
        summary.return_value = {
            "items": [{"product": self.product, "quantity": 1, "subtotal": Decimal("7.00")}],
            "subtotal": Decimal("7.00"),
            "coupon": None,
            "discount": Decimal("0.00"),
            "total": Decimal("7.00"),
        }
        with self.client.session_transaction() as logged_session:
            logged_session.update(
                user_id=7,
                user_name="Cliente",
                role="customer",
                pending_coupon_code="BEMVINDO10",
            )

        response = self.client.get("/checkout")

        self.assertEqual(response.status_code, 200)
        apply_coupon.assert_called_once_with("BEMVINDO10")
        with self.client.session_transaction() as logged_session:
            self.assertNotIn("pending_coupon_code", logged_session)


class AuthSessionTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = self.app.test_client()

    @patch("app.routes.auth.UserRepository.find_by_email")
    def test_customer_login_preserves_guest_cart(self, find_by_email):
        find_by_email.return_value = {
            "id": 7,
            "name": "Cliente",
            "email": "cliente@example.com",
            "password_hash": generate_password_hash("Senha123"),
            "role": "customer",
        }
        with self.client.session_transaction() as guest_session:
            guest_session["cart"] = {"1": 2, "6": 1}
            guest_session["pending_coupon_code"] = "BEMVINDO10"

        response = self.client.post(
            "/login",
            data={"email": "cliente@example.com", "password": "Senha123"},
        )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as logged_session:
            self.assertEqual(logged_session["user_id"], 7)
            self.assertEqual(logged_session["cart"], {"1": 2, "6": 1})
            self.assertEqual(logged_session["pending_coupon_code"], "BEMVINDO10")

    def test_checkout_redirects_guest_to_login_with_return_url(self):
        response = self.client.get("/checkout")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login?next=/checkout"))

    def test_logout_clears_session_without_success_toast(self):
        with self.client.session_transaction() as logged_session:
            logged_session.update(user_id=7, user_name="Cliente", role="customer")

        response = self.client.post("/sair")

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as logged_session:
            self.assertNotIn("user_id", logged_session)
            self.assertNotIn("_flashes", logged_session)

    @patch("app.routes.auth.UserRepository.create")
    def test_registration_preserves_checkout_return_url_and_cart(self, create_user):
        with self.client.session_transaction() as guest_session:
            guest_session["cart"] = {"1": 2}

        response = self.client.post(
            "/cadastro",
            data={
                "name": "Nova Cliente",
                "email": "nova@example.com",
                "phone": "(11) 91234-5678",
                "password": "Senha123",
                "next": "/checkout",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login?next=/checkout"))
        create_user.assert_called_once()
        with self.client.session_transaction() as guest_session:
            self.assertEqual(guest_session["cart"], {"1": 2})

    @patch("app.routes.auth.UserRepository.find_by_email")
    def test_login_returns_customer_to_checkout(self, find_by_email):
        find_by_email.return_value = {
            "id": 7,
            "name": "Cliente",
            "email": "cliente@example.com",
            "password_hash": generate_password_hash("Senha123"),
            "role": "customer",
        }
        with self.client.session_transaction() as guest_session:
            guest_session["cart"] = {"1": 2}

        response = self.client.post(
            "/login",
            data={
                "email": "cliente@example.com",
                "password": "Senha123",
                "next": "/checkout",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/checkout"))

    @patch("app.routes.auth.UserRepository.find_by_email")
    def test_login_rejects_external_return_url(self, find_by_email):
        find_by_email.return_value = {
            "id": 7,
            "name": "Cliente",
            "email": "cliente@example.com",
            "password_hash": generate_password_hash("Senha123"),
            "role": "customer",
        }

        response = self.client.post(
            "/login",
            data={
                "email": "cliente@example.com",
                "password": "Senha123",
                "next": "https://example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.location).path, "/")

    @patch("app.routes.auth.UserRepository.find")
    def test_account_page_shows_profile_and_orders_menu(self, find_user):
        find_user.return_value = {
            "id": 7,
            "name": "Cliente",
            "email": "cliente@example.com",
            "phone": "(11) 91234-5678",
            "role": "customer",
        }
        with self.client.session_transaction() as logged_session:
            logged_session.update(user_id=7, user_name="Cliente", role="customer")

        response = self.client.get("/minha-conta")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dados pessoais", response.data)
        self.assertIn(b"Meus pedidos", response.data)
        self.assertIn(b"cliente@example.com", response.data)
        self.assertIn(b'content="noindex, nofollow"', response.data)

    @patch("app.routes.auth.UserRepository.update_profile")
    @patch("app.routes.auth.UserRepository.find")
    def test_customer_can_update_profile(self, find_user, update_profile):
        find_user.return_value = {
            "id": 7,
            "name": "Cliente",
            "email": "cliente@example.com",
            "password_hash": generate_password_hash("Senha123"),
            "phone": "(11) 91234-5678",
            "role": "customer",
        }
        with self.client.session_transaction() as logged_session:
            logged_session.update(user_id=7, user_name="Cliente", role="customer")

        response = self.client.post(
            "/minha-conta",
            data={
                "intent": "profile",
                "email": "atualizada@example.com",
                "phone": "(21) 99876-5432",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/minha-conta"))
        update_profile.assert_called_once_with(7, "atualizada@example.com", "(21) 99876-5432")

    @patch("app.routes.auth.UserRepository.update_password")
    @patch("app.routes.auth.UserRepository.find")
    def test_customer_can_change_password(self, find_user, update_password):
        find_user.return_value = {
            "id": 7,
            "name": "Cliente",
            "email": "cliente@example.com",
            "password_hash": generate_password_hash("Senha123"),
            "phone": "(11) 91234-5678",
            "role": "customer",
        }
        with self.client.session_transaction() as logged_session:
            logged_session.update(user_id=7, user_name="Cliente", role="customer")

        response = self.client.post(
            "/minha-conta",
            data={
                "intent": "password",
                "current_password": "Senha123",
                "new_password": "NovaSenha456",
                "password_confirmation": "NovaSenha456",
            },
        )

        self.assertEqual(response.status_code, 302)
        stored_hash = update_password.call_args.args[1]
        self.assertEqual(update_password.call_args.args[0], 7)
        self.assertTrue(check_password_hash(stored_hash, "NovaSenha456"))


class SeoMetadataTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = self.app.test_client()

    @patch("app.routes.shop.ProductRepository.list_active", return_value=[])
    def test_catalog_has_public_search_metadata(self, _list_active):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CoffeeTime \xc2\xb7 Caf\xc3\xa9s especiais", response.data)
        self.assertIn(b'name="description"', response.data)
        self.assertIn(b'content="index, follow"', response.data)
        self.assertIn(b'rel="canonical"', response.data)
        self.assertIn(b'property="og:title"', response.data)

    @patch("app.routes.shop.ProductRepository.recommendations", return_value=[])
    @patch("app.routes.shop.ProductRepository.find")
    def test_product_uses_product_specific_metadata(self, find_product, _recommendations):
        find_product.return_value = {
            "id": 1,
            "name": "Espresso da Casa",
            "description": "Espresso encorpado de 60 ml.",
            "category": "Cafés",
            "price": Decimal("7.00"),
            "image_data": None,
            "image_mime": None,
        }

        response = self.client.get("/produto/1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Espresso da Casa \xc2\xb7 CoffeeTime", response.data)
        self.assertIn(b"Espresso encorpado de 60 ml.", response.data)
        self.assertIn(b'content="product"', response.data)

if __name__ == "__main__":
    unittest.main()
