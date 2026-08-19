import unittest
from decimal import Decimal
from unittest.mock import patch

from flask import Flask, session

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


if __name__ == "__main__":
    unittest.main()
