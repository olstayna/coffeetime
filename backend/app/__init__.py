import base64
from pathlib import Path

from flask import Flask, session

from app.config import Config
from app.database import close_db, init_database_command
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.shop import shop_bp


def create_app(config_class=Config):
    project_root = Path(__file__).resolve().parents[2]
    app = Flask(
        __name__,
        template_folder=str(project_root / "frontend" / "templates"),
        static_folder=str(project_root / "frontend" / "static"),
    )
    app.config.from_object(config_class)

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_database_command)

    @app.template_filter("image_data_uri")
    def image_data_uri(product):
        image_data = product.get("image_data") if product else None
        if not image_data:
            return ""
        mime_type = product.get("image_mime") or "image/jpeg"
        encoded = base64.b64encode(image_data).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @app.context_processor
    def cart_preview():
        from app.services import CartService

        if not session.get("cart"):
            return {"cart_preview": {"items": [], "total": 0}, "cart_count": 0}
        return {
            "cart_preview": CartService.summary(),
            "cart_count": sum(session["cart"].values()),
        }

    return app
