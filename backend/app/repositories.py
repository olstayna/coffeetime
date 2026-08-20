from app.database import execute, fetch_all, fetch_one, get_db


class ProductRepository:
    FIELDS = "id, name, description, category, price, image_data, image_mime, active, created_at"
    SUMMARY_FIELDS = "id, name, description, category, price, active, created_at"

    @staticmethod
    def list_active(search="", category=""):
        query = f"SELECT {ProductRepository.FIELDS} FROM products WHERE active = 1"
        params = []
        if search:
            query += " AND (name LIKE %s OR category LIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])
        if category:
            query += " AND category = %s"
            params.append(category)
        return fetch_all(query + " ORDER BY category, name", tuple(params))

    @staticmethod
    def list_all():
        return fetch_all(f"SELECT {ProductRepository.SUMMARY_FIELDS} FROM products ORDER BY name")

    @staticmethod
    def find(product_id, active_only=False):
        suffix = " AND active = 1" if active_only else ""
        return fetch_one(f"SELECT {ProductRepository.FIELDS} FROM products WHERE id = %s" + suffix, (product_id,))

    @staticmethod
    def recommendations(product_id, limit=4):
        return fetch_all(
            f"SELECT {ProductRepository.FIELDS} FROM products WHERE active = 1 AND id <> %s ORDER BY RAND() LIMIT %s",
            (product_id, limit),
        )

    @staticmethod
    def save(data, product_id=None):
        values = (data["name"], data["description"], data["category"], data["price"], data["active"])
        if product_id:
            if data.get("image_data") is not None:
                execute("UPDATE products SET name=%s, description=%s, category=%s, price=%s, active=%s, image_data=%s, image_mime=%s WHERE id=%s", values + (data["image_data"], data["image_mime"], product_id))
            else:
                execute("UPDATE products SET name=%s, description=%s, category=%s, price=%s, active=%s WHERE id=%s", values + (product_id,))
            return product_id
        return execute("INSERT INTO products (name, description, category, price, active, image_data, image_mime) VALUES (%s,%s,%s,%s,%s,%s,%s)", values + (data["image_data"], data["image_mime"]))


class UserRepository:
    @staticmethod
    def list_customers():
        return fetch_all("SELECT id, name, email, phone, created_at FROM users WHERE role='customer' ORDER BY created_at DESC")

    @staticmethod
    def find_by_email(email):
        return fetch_one("SELECT * FROM users WHERE email = %s", (email,))

    @staticmethod
    def find(user_id):
        return fetch_one("SELECT id, name, email, password_hash, phone, role, created_at FROM users WHERE id = %s", (user_id,))

    @staticmethod
    def create(name, email, password_hash, phone):
        return execute("INSERT INTO users (name, email, password_hash, phone) VALUES (%s,%s,%s,%s)", (name, email, password_hash, phone))

    @staticmethod
    def update_profile(user_id, email, phone):
        return execute(
            "UPDATE users SET email=%s, phone=%s WHERE id=%s AND role='customer'",
            (email, phone, user_id),
        )

    @staticmethod
    def update_password(user_id, password_hash):
        return execute(
            "UPDATE users SET password_hash=%s WHERE id=%s AND role='customer'",
            (password_hash, user_id),
        )

    @staticmethod
    def delete_customer(user_id):
        db = get_db()
        try:
            execute("DELETE FROM orders WHERE user_id=%s", (user_id,), commit=False)
            cursor = db.cursor()
            cursor.execute("DELETE FROM users WHERE id=%s AND role='customer'", (user_id,))
            deleted = cursor.rowcount
            cursor.close()
            db.commit()
            return bool(deleted)
        except Exception:
            db.rollback()
            raise


class CouponRepository:
    @staticmethod
    def list_all():
        return fetch_all("SELECT * FROM coupons ORDER BY active DESC, code")

    @staticmethod
    def create(data):
        return execute(
            "INSERT INTO coupons (code,discount_type,discount_value,minimum_amount,expires_at,first_order_only,active) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (data["code"], data["discount_type"], data["discount_value"], data["minimum_amount"], data["expires_at"], data["first_order_only"], data["active"]),
        )

    @staticmethod
    def delete(coupon_id):
        return execute("DELETE FROM coupons WHERE id=%s", (coupon_id,))

    @staticmethod
    def find_valid(code):
        return fetch_one(
            """SELECT * FROM coupons
               WHERE code = %s AND active = 1
               AND (expires_at IS NULL OR expires_at > NOW())""",
            (code.upper(),),
        )


class OrderRepository:
    @staticmethod
    def has_orders_for_user(user_id):
        row = fetch_one("SELECT EXISTS(SELECT 1 FROM orders WHERE user_id=%s) AS has_orders", (user_id,))
        return bool(row and row["has_orders"])

    @staticmethod
    def list_for_user(user_id):
        return fetch_all("SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC", (user_id,))

    @staticmethod
    def list_all():
        return fetch_all("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.created_at DESC")

    @staticmethod
    def find_for_user(order_id, user_id):
        order = fetch_one("SELECT * FROM orders WHERE id=%s AND user_id=%s", (order_id, user_id))
        if order:
            order["items"] = fetch_all("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
        return order
