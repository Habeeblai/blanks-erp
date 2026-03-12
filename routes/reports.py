"""Reports blueprint — daily, monthly, product profit, fast movers, restock."""

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime, date, timedelta
from models import db, Sale, SaleItem, Variant, InventoryBatch, Expense, Product, Brand, Color, Size
from routes.auth import admin_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/daily')
@login_required
@admin_required
def daily():
    date_str = request.args.get('date', date.today().isoformat())
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = date.today()

    sales = Sale.query.filter(
        func.date(Sale.date) == report_date
    ).order_by(Sale.date.desc()).all()

    expenses = Expense.query.filter_by(date=report_date).all()
    total_expenses = sum(float(e.amount) for e in expenses)
    total_revenue = sum(s.total_revenue() for s in sales)
    total_profit = sum(s.total_profit() for s in sales)
    net_profit = total_profit - total_expenses

    return render_template('reports_daily.html',
                           report_date=report_date,
                           sales=sales,
                           expenses=expenses,
                           total_revenue=total_revenue,
                           total_profit=total_profit,
                           total_expenses=total_expenses,
                           net_profit=net_profit)


@reports_bp.route('/monthly')
@login_required
@admin_required
def monthly():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    sales = Sale.query.filter(
        Sale.date >= start, Sale.date < end
    ).order_by(Sale.date).all()

    expenses = Expense.query.filter(
        Expense.date >= start, Expense.date < end
    ).all()

    total_revenue = sum(s.total_revenue() for s in sales)
    total_profit = sum(s.total_profit() for s in sales)
    total_expenses = sum(float(e.amount) for e in expenses)
    net_profit = total_profit - total_expenses

    months = [(y, m) for y in range(today.year - 1, today.year + 1)
              for m in range(1, 13)]

    return render_template('reports_monthly.html',
                           year=year, month=month,
                           sales=sales, expenses=expenses,
                           total_revenue=total_revenue,
                           total_profit=total_profit,
                           total_expenses=total_expenses,
                           net_profit=net_profit,
                           months=months)


@reports_bp.route('/products')
@login_required
@admin_required
def products():
    rows = (db.session.query(
                Variant,
                func.sum(SaleItem.quantity).label('units_sold'),
                func.sum(SaleItem.profit).label('total_profit'),
                func.sum(SaleItem.selling_price_at_sale * SaleItem.quantity).label('total_revenue'),
            )
            .join(SaleItem, SaleItem.variant_id == Variant.id)
            .group_by(Variant.id)
            .order_by(func.sum(SaleItem.profit).desc())
            .all())

    return render_template('reports_products.html', rows=rows)


@reports_bp.route('/fast_movers')
@login_required
@admin_required
def fast_movers():
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)

    rows = (db.session.query(
                Variant,
                func.sum(SaleItem.quantity).label('units_sold'),
            )
            .join(SaleItem, SaleItem.variant_id == Variant.id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(Sale.date >= since)
            .group_by(Variant.id)
            .order_by(func.sum(SaleItem.quantity).desc())
            .limit(20)
            .all())

    return render_template('reports_fast_movers.html', rows=rows, days=days)


@reports_bp.route('/restock')
@login_required
@admin_required
def restock():
    threshold = request.args.get('threshold', 5, type=int)
    all_variants = Variant.query.all()
    low = [(v, v.total_stock()) for v in all_variants if v.total_stock() <= threshold]
    low.sort(key=lambda x: x[1])

    return render_template('reports_restock.html', low_stock=low, threshold=threshold)
