"""
Blanks Store ERP — Flask application factory.
"""

import os
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from config import config
from models import db, User

login_manager = LoginManager()
migrate = Migrate()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.products import products_bp
    from routes.inventory import inventory_bp
    from routes.sales import sales_bp
    from routes.reports import reports_bp
    from routes.expenses import expenses_bp
    from routes.staff import staff_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(staff_bp)

    with app.app_context():
        db.create_all()
        _migrate_existing_db()
        _migrate_skus()
        _seed_defaults()

    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def _run_sql(sql, params=None):
    """Run a single DDL statement in its own transaction, ignore errors."""
    from sqlalchemy import text
    try:
        with db.engine.connect() as conn:
            conn.execute(text(sql), params or {})
            conn.commit()
    except Exception:
        pass


def _migrate_existing_db():
    """Fix old database structure to match new models."""
    from sqlalchemy import inspect
    inspector = inspect(db.engine)

    # Drop old inventory table — replaced by inventory_batches
    if inspector.has_table('inventory'):
        _run_sql("DROP TABLE inventory CASCADE")

    # Remove old cost_price column from variants (now lives on batches)
    if inspector.has_table('variants'):
        cols = [c['name'] for c in inspector.get_columns('variants')]
        if 'cost_price' in cols:
            _run_sql("ALTER TABLE variants DROP COLUMN IF EXISTS cost_price")

    # Add role column to users
    if inspector.has_table('users'):
        cols = [c['name'] for c in inspector.get_columns('users')]
        if 'role' not in cols:
            _run_sql("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'admin'")

    # Add recorded_by and user_id to sales
    if inspector.has_table('sales'):
        cols = [c['name'] for c in inspector.get_columns('sales')]
        if 'recorded_by' not in cols:
            _run_sql("ALTER TABLE sales ADD COLUMN recorded_by VARCHAR(80)")
        if 'user_id' not in cols:
            _run_sql("ALTER TABLE sales ADD COLUMN user_id INTEGER")

    # Add batch_id to sale_items
    if inspector.has_table('sale_items'):
        cols = [c['name'] for c in inspector.get_columns('sale_items')]
        if 'batch_id' not in cols:
            _run_sql("ALTER TABLE sale_items ADD COLUMN batch_id INTEGER")


def _migrate_skus():
    """One-time migration — rename all existing SKUs to new product-based format."""
    from models import Variant, Product
    try:
        products = Product.query.all()
        for product in products:
            prefix = product.name.upper().replace(' ', '')[:7]
            variants = Variant.query.filter_by(product_id=product.id).order_by(Variant.id).all()
            for i, v in enumerate(variants, start=1):
                new_sku = f"{prefix}-{i}"
                if v.sku != new_sku:
                    v.sku = new_sku
        db.session.commit()
    except Exception:
        db.session.rollback()


def _seed_defaults():
    """Create default admin account and lookup data if the database is empty."""
    from models import User, Product, Brand, Color, Size

    if not User.query.filter_by(role='admin').first():
        admin = User(username='habeeblai', role='admin')
        admin.set_password('blanksstore244?')
        db.session.add(admin)

    if not Product.query.first():
        for name, cat in [('T-Shirt', 'Tops'), ('Polo Shirt', 'Tops'), ('Cap', 'Headwear')]:
            db.session.add(Product(name=name, category=cat))

    if not Brand.query.first():
        for b in ['Gildan', 'Bella+Canvas', 'Next Level', 'Port & Company']:
            db.session.add(Brand(name=b))

    if not Color.query.first():
        for c in ['Black', 'White', 'Navy', 'Red', 'Grey', 'Royal Blue']:
            db.session.add(Color(name=c))

    if not Size.query.first():
        for s in ['XS', 'S', 'M', 'L', 'XL', 'XXL']:
            db.session.add(Size(name=s))

    db.session.commit()


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
