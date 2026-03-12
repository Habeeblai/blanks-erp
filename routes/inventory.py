"""Inventory blueprint — batch tracking, table view, grid view, stock adjustments."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime
from models import db, Variant, InventoryBatch, Product, Brand, Color, Size
from routes.auth import admin_required

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


def _get_filters():
    return {
        'q': request.args.get('q', '').strip(),
        'product_id': request.args.get('product_id', type=int),
        'brand_id': request.args.get('brand_id', type=int),
        'color_id': request.args.get('color_id', type=int),
        'size_id': request.args.get('size_id', type=int),
    }


# ---------------------------------------------------------------------------
# Table view
# ---------------------------------------------------------------------------

@inventory_bp.route('/')
@login_required
@admin_required
def index():
    filters = _get_filters()
    page = request.args.get('page', 1, type=int)

    query = (Variant.query
             .join(Product).join(Brand).join(Color).join(Size))

    if filters['q']:
        query = query.filter(Variant.sku.ilike(f"%{filters['q']}%"))
    if filters['product_id']:
        query = query.filter(Variant.product_id == filters['product_id'])
    if filters['brand_id']:
        query = query.filter(Variant.brand_id == filters['brand_id'])
    if filters['color_id']:
        query = query.filter(Variant.color_id == filters['color_id'])
    if filters['size_id']:
        query = query.filter(Variant.size_id == filters['size_id'])

    pagination = query.order_by(Variant.sku).paginate(
        page=page, per_page=50, error_out=False)

    products = Product.query.order_by(Product.name).all()
    brands = Brand.query.order_by(Brand.name).all()
    colors = Color.query.order_by(Color.name).all()
    sizes = Size.query.order_by(Size.name).all()

    return render_template(
        'inventory.html',
        pagination=pagination,
        variants=pagination.items,
        filters=filters,
        products=products, brands=brands, colors=colors, sizes=sizes,
    )


# ---------------------------------------------------------------------------
# Batch detail view — all batches for a single variant
# ---------------------------------------------------------------------------

@inventory_bp.route('/batches/<int:variant_id>')
@login_required
@admin_required
def batches(variant_id):
    variant = Variant.query.get_or_404(variant_id)
    all_batches = InventoryBatch.query.filter_by(variant_id=variant_id)\
        .order_by(InventoryBatch.date_added.asc()).all()
    return render_template('inventory_batches.html',
                           variant=variant, batches=all_batches)


# ---------------------------------------------------------------------------
# Add new batch (restock)
# ---------------------------------------------------------------------------

@inventory_bp.route('/restock/<int:variant_id>', methods=['POST'])
@login_required
@admin_required
def restock(variant_id):
    """Add a new stock batch at a (possibly different) cost price."""
    variant = Variant.query.get_or_404(variant_id)
    qty = request.form.get('quantity', 0, type=int)
    cost_price = request.form.get('cost_price', 0, type=float)
    selling_price = request.form.get('selling_price', float(variant.selling_price), type=float)
    notes = request.form.get('notes', '').strip()

    if qty <= 0:
        flash('Quantity must be positive.', 'danger')
        return redirect(request.referrer or url_for('inventory.index'))
    if cost_price <= 0:
        flash('Cost price must be greater than zero.', 'danger')
        return redirect(request.referrer or url_for('inventory.index'))

    # Get next batch number for this variant
    last_batch = InventoryBatch.query.filter_by(variant_id=variant_id)\
        .order_by(InventoryBatch.batch_number.desc()).first()
    next_batch_num = (last_batch.batch_number + 1) if last_batch else 1

    batch = InventoryBatch(
        variant_id=variant_id,
        batch_number=next_batch_num,
        date_added=datetime.utcnow(),
        cost_price=cost_price,
        selling_price=selling_price,
        quantity=qty,
        notes=notes,
    )
    db.session.add(batch)

    # Update variant default selling price to latest
    variant.selling_price = selling_price
    db.session.commit()

    flash(f'Batch #{next_batch_num} added — {qty} units at ₦{cost_price:.2f}.', 'success')
    return redirect(request.referrer or url_for('inventory.index'))


# ---------------------------------------------------------------------------
# Adjust a specific batch quantity
# ---------------------------------------------------------------------------

@inventory_bp.route('/batch/adjust/<int:batch_id>', methods=['POST'])
@login_required
@admin_required
def adjust_batch(batch_id):
    batch = InventoryBatch.query.get_or_404(batch_id)
    qty = request.form.get('quantity', 0, type=int)
    if qty < 0:
        flash('Quantity cannot be negative.', 'danger')
    else:
        batch.quantity = qty
        db.session.commit()
        flash(f'Batch #{batch.batch_number} updated to {qty} units.', 'success')
    return redirect(request.referrer or url_for('inventory.batches',
                                                variant_id=batch.variant_id))


# ---------------------------------------------------------------------------
# Delete an empty batch
# ---------------------------------------------------------------------------

@inventory_bp.route('/batch/delete/<int:batch_id>', methods=['POST'])
@login_required
@admin_required
def delete_batch(batch_id):
    batch = InventoryBatch.query.get_or_404(batch_id)
    variant_id = batch.variant_id
    db.session.delete(batch)
    db.session.commit()
    flash('Batch deleted.', 'info')
    return redirect(url_for('inventory.batches', variant_id=variant_id))


# ---------------------------------------------------------------------------
# Grid view
# ---------------------------------------------------------------------------

@inventory_bp.route('/grid')
@login_required
@admin_required
def grid():
    product_id = request.args.get('product_id', type=int)
    brand_id = request.args.get('brand_id', type=int)

    products = Product.query.order_by(Product.name).all()
    brands = Brand.query.order_by(Brand.name).all()

    grid_data = None

    if product_id and brand_id:
        variants = (Variant.query
                    .filter_by(product_id=product_id, brand_id=brand_id)
                    .join(Color).join(Size).all())

        color_ids = sorted(set(v.color_id for v in variants))
        size_ids = sorted(set(v.size_id for v in variants))
        colors_in_grid = Color.query.filter(Color.id.in_(color_ids)).order_by(Color.name).all()
        sizes_in_grid = Size.query.filter(Size.id.in_(size_ids)).order_by(Size.name).all()

        var_map = {(v.color_id, v.size_id): v for v in variants}

        grid_data = {
            'sizes': sizes_in_grid,
            'rows': [
                {
                    'color': color,
                    'cells': [
                        {'variant': var_map.get((color.id, size.id))}
                        for size in sizes_in_grid
                    ]
                }
                for color in colors_in_grid
            ]
        }

    return render_template(
        'inventory_grid.html',
        products=products, brands=brands,
        product_id=product_id, brand_id=brand_id,
        grid_data=grid_data,
    )


# ---------------------------------------------------------------------------
# AJAX — grid update (sets total stock, adjusts newest batch)
# ---------------------------------------------------------------------------

@inventory_bp.route('/grid/update', methods=['POST'])
@login_required
@admin_required
def grid_update():
    data = request.get_json()
    variant_id = data.get('variant_id')
    quantity = data.get('quantity')

    if variant_id is None or quantity is None or int(quantity) < 0:
        return jsonify({'error': 'Invalid data'}), 400

    variant = Variant.query.get(variant_id)
    if not variant:
        return jsonify({'error': 'Variant not found'}), 404

    # Find the most recent batch and set its quantity
    latest_batch = InventoryBatch.query.filter_by(variant_id=variant_id)\
        .order_by(InventoryBatch.date_added.desc()).first()

    if latest_batch:
        latest_batch.quantity = int(quantity)
    else:
        # No batch exists — create a default one
        batch = InventoryBatch(
            variant_id=variant_id,
            batch_number=1,
            cost_price=variant.selling_price,
            selling_price=variant.selling_price,
            quantity=int(quantity),
        )
        db.session.add(batch)

    db.session.commit()
    return jsonify({'success': True, 'quantity': variant.total_stock()})
