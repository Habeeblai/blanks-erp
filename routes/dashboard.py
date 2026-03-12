"""Dashboard blueprint — KPI summary cards."""

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime, date
from models import db, Variant, InventoryBatch, Sale, SaleItem, Expense
from routes.auth import admin_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
@admin_required
def index():
    today = date.today()

    # Total variants
    total_variants = Variant.query.count()

    # Total units in stock
    total_units = db.session.query(func.sum(InventoryBatch.quantity)).scalar() or 0

    # Inventory worth at cost
    inv_worth = db.session.query(
        func.sum(InventoryBatch.quantity * InventoryBatch.cost_price)
    ).scalar() or 0

    # Potential revenue if all sold
    sales_value = db.session.query(
        func.sum(InventoryBatch.quantity * InventoryBatch.selling_price)
    ).scalar() or 0

    potential_profit = float(sales_value) - float(inv_worth)

    # Today's revenue and profit
    today_sales = Sale.query.filter(func.date(Sale.date) == today).all()
    today_revenue = sum(s.total_revenue() for s in today_sales)
    today_profit = sum(s.total_profit() for s in today_sales)

    # Low stock variants (total stock <= 10)
    all_variants = Variant.query.all()
    low_stock = [(v, v.total_stock()) for v in all_variants if 0 < v.total_stock() <= 10]
    low_stock.sort(key=lambda x: x[1])

    return render_template('dashboard.html',
                           today=today,
                           total_variants=total_variants,
                           total_units=int(total_units),
                           inv_worth=float(inv_worth),
                           sales_value=float(sales_value),
                           potential_profit=potential_profit,
                           today_revenue=today_revenue,
                           today_profit=today_profit,
                           low_stock=low_stock)
