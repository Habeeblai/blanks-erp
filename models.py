"""
Database models for Blanks Store ERP.
Includes batch tracking, staff roles, and normalized inventory design.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    """Admin or Staff user."""
    __tablename__ = 'users'

    ROLE_ADMIN = 'admin'
    ROLE_STAFF = 'staff'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='admin')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_staff(self):
        return self.role == self.ROLE_STAFF

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# ---------------------------------------------------------------------------
# Product Catalog
# ---------------------------------------------------------------------------

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)

    variants = db.relationship('Variant', backref='product', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Product {self.name}>'


class Brand(db.Model):
    __tablename__ = 'brands'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    variants = db.relationship('Variant', backref='brand', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Brand {self.name}>'


class Color(db.Model):
    __tablename__ = 'colors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    variants = db.relationship('Variant', backref='color', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Color {self.name}>'


class Size(db.Model):
    __tablename__ = 'sizes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)

    variants = db.relationship('Variant', backref='size', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Size {self.name}>'


# ---------------------------------------------------------------------------
# Variants — one clean SKU per product/brand/color/size combination
# ---------------------------------------------------------------------------

class Variant(db.Model):
    """
    One variant = one SKU. Stock is tracked across multiple batches.
    Total stock = sum of all batch quantities.
    """
    __tablename__ = 'variants'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False, index=True)
    color_id = db.Column(db.Integer, db.ForeignKey('colors.id'), nullable=False, index=True)
    size_id = db.Column(db.Integer, db.ForeignKey('sizes.id'), nullable=False, index=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    # Default selling price — can be overridden per batch
    selling_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    batches = db.relationship('InventoryBatch', backref='variant', lazy='dynamic',
                              cascade='all, delete-orphan',
                              order_by='InventoryBatch.date_added')
    sale_items = db.relationship('SaleItem', backref='variant', lazy='dynamic',
                                 cascade='all, delete-orphan')

    def total_stock(self):
        """Sum of all batch quantities."""
        return sum(b.quantity for b in self.batches if b.quantity > 0)

    def total_stock_value(self):
        """Total inventory value at cost across all batches."""
        return sum(b.quantity * float(b.cost_price) for b in self.batches if b.quantity > 0)

    def active_batches(self):
        """Batches that still have stock."""
        return [b for b in self.batches if b.quantity > 0]

    def latest_batch(self):
        """Return most recently added batch."""
        from sqlalchemy import desc
        return InventoryBatch.query.filter_by(variant_id=self.id)\
            .order_by(desc(InventoryBatch.date_added)).first()

    def oldest_batch(self):
        """Return oldest batch with stock (FIFO)."""
        for b in self.batches.order_by(InventoryBatch.date_added.asc()):
            if b.quantity > 0:
                return b
        return None

    def display_name(self):
        return f"{self.product.name} / {self.brand.name} / {self.color.name} / {self.size.name}"

    def __repr__(self):
        return f'<Variant {self.sku}>'


# ---------------------------------------------------------------------------
# Inventory Batches — each restock creates a new batch
# ---------------------------------------------------------------------------

class InventoryBatch(db.Model):
    """
    A batch of stock purchased at a specific cost price on a specific date.
    One variant can have many batches at different prices.
    FIFO is used when selling — oldest batch is depleted first.
    """
    __tablename__ = 'inventory_batches'

    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'),
                           nullable=False, index=True)
    batch_number = db.Column(db.Integer, nullable=False, default=1)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    cost_price = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.String(255))

    def stock_value(self):
        return float(self.quantity) * float(self.cost_price)

    def __repr__(self):
        return f'<Batch {self.variant_id} #{self.batch_number} qty={self.quantity}>'


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    notes = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    recorded_by = db.Column(db.String(80), nullable=True)

    items = db.relationship('SaleItem', backref='sale', lazy='joined',
                            cascade='all, delete-orphan')

    def total_revenue(self):
        return sum(float(item.selling_price_at_sale) * item.quantity for item in self.items)

    def total_profit(self):
        return sum(float(item.profit) for item in self.items)

    def __repr__(self):
        return f'<Sale {self.id} {self.date}>'


class SaleItem(db.Model):
    """
    Line item within a sale.
    Records which batch was used for accurate profit calculation.
    """
    __tablename__ = 'sale_items'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variants.id'), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('inventory_batches.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    cost_price_at_sale = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price_at_sale = db.Column(db.Numeric(10, 2), nullable=False)
    profit = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f'<SaleItem sale={self.sale_id} variant={self.variant_id}>'


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

class Expense(db.Model):
    __tablename__ = 'expenses'

    CATEGORIES = [
        'Rent', 'Electricity', 'Salary', 'Transport',
        'Marketing', 'Miscellaneous'
    ]

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f'<Expense {self.category} {self.amount}>'
