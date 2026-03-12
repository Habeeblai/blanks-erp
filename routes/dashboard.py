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

    # Total inventory value at cost
    inventory_worth = db.session.query(
        func.sum(InventoryBatch.quantity * InventoryBatch.cost_price)
    ).scalar() or 0

    # Potential revenue (sell all stock at selling price)
    potential_revenue = db.session.query(
        func.sum(InventoryBatch.quantity * InventoryBatch.selling_price)
    ).scalar() or 0

    potential_profit = float(potential_revenue) - float(inventory_worth)

    # Today's revenue and profit
    today_sales = Sale.query.filter(
        func.date(Sale.date) == today
    ).all()

    today_revenue = sum(s.total_revenue() for s in today_sales)
    today_profit = sum(s.total_profit() for s in today_sales)

    # Low stock variants (total stock <= 5 across all batches)
    all_variants = Variant.query.all()
    low_stock = [v for v in all_variants if 0 < v.total_stock() <= 5]
    out_of_stock = [v for v in all_variants if v.total_stock() == 0]

    # Recent sales
    recent_sales = Sale.query.order_by(Sale.date.desc()).limit(5).all()

    return render_template('dashboard.html',
                           inventory_worth=inventory_worth,
                           potential_profit=potential_profit,
                           today_revenue=today_revenue,
                           today_profit=today_profit,
                           low_stock=low_stock,
                           out_of_stock=out_of_stock,
                           recent_sales=recent_sales)
