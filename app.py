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
        _seed_defaults()

    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def _seed_defaults():
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
