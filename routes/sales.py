"""Sales blueprint — FIFO batch deduction when recording sales."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Sale, SaleItem, Variant, InventoryBatch, Product, Brand, Color, Size
from routes.auth import admin_required

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


def _deduct_fifo(variant, qty_needed):
    """
    Deduct qty_needed units from variant batches using FIFO.
    Returns list of (batch, qty_used, cost_price, selling_price) tuples.
    Raises ValueError if insufficient stock.
    """
    batches = InventoryBatch.query.filter_by(variant_id=variant.id)\
        .filter(InventoryBatch.quantity > 0)\
        .order_by(InventoryBatch.date_added.asc()).all()

    total_available = sum(b.quantity for b in batches)
    if total_available < qty_needed:
        raise ValueError(f'Only {total_available} units available for {variant.sku}.')

    deductions = []
    remaining = qty_needed
    for batch in batches:
        if remaining <= 0:
            break
        use = min(batch.quantity, remaining)
        deductions.append((batch, use, float(batch.cost_price), float(batch.selling_price)))
        batch.quantity -= use
        remaining -= use

    return deductions


@sales_bp.route('/')
@login_required
@admin_required
def index():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')

    query = Sale.query.order_by(Sale.date.desc())
    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Sale.date) == d)
        except ValueError:
            pass

    pagination = query.paginate(page=page, per_page=30, error_out=False)
    return render_template('sales.html', pagination=pagination,
                           sales=pagination.items, date_filter=date_filter)


@sales_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    """Record a new sale — accessible by both admin and staff."""
    if request.method == 'POST':
        variant_ids = request.form.getlist('variant_id[]')
        quantities = request.form.getlist('quantity[]')
        notes = request.form.get('notes', '').strip()

        if not variant_ids:
            flash('Add at least one item.', 'danger')
            return redirect(url_for('sales.new_sale'))

        sale = Sale(
            date=datetime.utcnow(),
            notes=notes,
            user_id=current_user.id,
            recorded_by=current_user.username,
        )
        db.session.add(sale)
        db.session.flush()

        errors = []
        for vid, qty_str in zip(variant_ids, quantities):
            try:
                qty = int(qty_str)
                if qty <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            variant = Variant.query.get(int(vid))
            if not variant:
                continue

            try:
                deductions = _deduct_fifo(variant, qty)
            except ValueError as e:
                errors.append(str(e))
                continue

            # Create one SaleItem per batch deducted (for accurate profit)
            for batch, used_qty, cost, sell in deductions:
                profit = (sell - cost) * used_qty
                db.session.add(SaleItem(
                    sale_id=sale.id,
                    variant_id=variant.id,
                    batch_id=batch.id,
                    quantity=used_qty,
                    cost_price_at_sale=cost,
                    selling_price_at_sale=sell,
                    profit=profit,
                ))

        if errors:
            db.session.rollback()
            for e in errors:
                flash(e, 'danger')
            return redirect(url_for('sales.new_sale'))

        db.session.commit()
        flash('Sale recorded successfully.', 'success')

        if current_user.is_staff():
            return redirect(url_for('staff.sales'))
        return redirect(url_for('sales.index'))

    # GET
    variants = (Variant.query
                .join(Product).join(Brand).join(Color).join(Size)
                .all())
    # Only show variants that have stock
    variants = [v for v in variants if v.total_stock() > 0]

    return render_template('new_sale.html', variants=variants)


@sales_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_sale(id):
    """Delete a sale and restore stock to the correct batches."""
    sale = Sale.query.get_or_404(id)
    for item in sale.items:
        if item.batch_id:
            batch = InventoryBatch.query.get(item.batch_id)
            if batch:
                batch.quantity += item.quantity
        else:
            # Fallback — restore to latest batch
            latest = InventoryBatch.query.filter_by(variant_id=item.variant_id)\
                .order_by(InventoryBatch.date_added.desc()).first()
            if latest:
                latest.quantity += item.quantity
    db.session.delete(sale)
    db.session.commit()
    flash('Sale deleted and stock restored.', 'info')
    return redirect(url_for('sales.index'))


@sales_bp.route('/api/variant_info/<int:variant_id>')
@login_required
def variant_info(variant_id):
    v = Variant.query.get_or_404(variant_id)
    return jsonify({
        'sku': v.sku,
        'display_name': v.display_name(),
        'selling_price': float(v.selling_price),
        'stock': v.total_stock(),
    })
