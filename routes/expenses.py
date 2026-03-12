"""Expenses blueprint — track operating costs."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from datetime import date
from models import db, Expense

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')


@expenses_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    month = request.args.get('month', '')

    query = Expense.query.order_by(Expense.date.desc())

    if category:
        query = query.filter(Expense.category == category)
    if month:
        try:
            year, mon = month.split('-')
            from sqlalchemy import extract
            query = query.filter(
                extract('year', Expense.date) == int(year),
                extract('month', Expense.date) == int(mon),
            )
        except Exception:
            pass

    pagination = query.paginate(page=page, per_page=30, error_out=False)
    total = sum(float(e.amount) for e in pagination.items)

    return render_template('expenses.html',
                           pagination=pagination,
                           expenses=pagination.items,
                           categories=Expense.CATEGORIES,
                           category=category,
                           month=month,
                           total=total,
                           today=date.today())


@expenses_bp.route('/add', methods=['POST'])
@login_required
def add():
    date_str = request.form.get('date', date.today().isoformat())
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    amount_str = request.form.get('amount', '0')

    try:
        exp_date = date.fromisoformat(date_str)
        amount = float(amount_str)
    except (ValueError, TypeError):
        flash('Invalid date or amount.', 'danger')
        return redirect(url_for('expenses.index'))

    if not category or amount <= 0:
        flash('Category and positive amount required.', 'danger')
        return redirect(url_for('expenses.index'))

    db.session.add(Expense(date=exp_date, category=category,
                           description=description, amount=amount))
    db.session.commit()
    flash('Expense recorded.', 'success')
    return redirect(url_for('expenses.index'))


@expenses_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    exp = Expense.query.get_or_404(id)
    db.session.delete(exp)
    db.session.commit()
    flash('Expense deleted.', 'info')
    return redirect(url_for('expenses.index'))
