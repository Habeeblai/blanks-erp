"""Products blueprint — manage products, brands, colors, sizes and variants."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models import db, Product, Brand, Color, Size, Variant, InventoryBatch, SaleItem
from routes.auth import admin_required

products_bp = Blueprint('products', __name__, url_prefix='/products')


def _generate_sku(product):
    """Generate SKU like TSHIRT-1, TSHIRT-2, CAP-1 etc."""
    prefix = product.name.upper().replace(' ', '')[:7]
    # Find highest existing number for this product to avoid collisions
    existing = Variant.query.filter_by(product_id=product.id).all()
    if not existing:
        return f"{prefix}-1"
    # Get all existing numbers for this prefix
    nums = []
    for v in existing:
        parts = v.sku.rsplit('-', 1)
        if len(parts) == 2 and parts[1].isdigit():
            nums.append(int(parts[1]))
    next_num = (max(nums) + 1) if nums else 1
    return f"{prefix}-{next_num}"


# ---------------------------------------------------------------------------
# Products page
# ---------------------------------------------------------------------------

@products_bp.route('/')
@login_required
@admin_required
def index():
    products = Product.query.order_by(Product.name).all()
    brands = Brand.query.order_by(Brand.name).all()
    colors = Color.query.order_by(Color.name).all()
    sizes = Size.query.order_by(Size.name).all()
    return render_template('products.html',
                           products=products, brands=brands,
                           colors=colors, sizes=sizes)


# --- Product CRUD ---
@products_bp.route('/add_product', methods=['POST'])
@login_required
@admin_required
def add_product():
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    if not name:
        flash('Product name required.', 'danger')
    else:
        db.session.add(Product(name=name, category=category))
        db.session.commit()
        flash(f'Product "{name}" added.', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/edit_product/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_product(id):
    p = Product.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    if not name:
        flash('Product name cannot be empty.', 'danger')
    else:
        p.name = name
        p.category = category
        db.session.commit()
        flash(f'Product updated to "{name}".', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/delete_product/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    p = Product.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Product deleted.', 'info')
    return redirect(url_for('products.index'))


# --- Brand CRUD ---
@products_bp.route('/add_brand', methods=['POST'])
@login_required
@admin_required
def add_brand():
    name = request.form.get('name', '').strip()
    if name:
        db.session.add(Brand(name=name))
        db.session.commit()
        flash(f'Brand "{name}" added.', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/edit_brand/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_brand(id):
    b = Brand.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Brand name cannot be empty.', 'danger')
    else:
        b.name = name
        db.session.commit()
        flash(f'Brand updated to "{name}".', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/delete_brand/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_brand(id):
    b = Brand.query.get_or_404(id)
    db.session.delete(b)
    db.session.commit()
    flash('Brand deleted.', 'info')
    return redirect(url_for('products.index'))


# --- Color CRUD ---
@products_bp.route('/add_color', methods=['POST'])
@login_required
@admin_required
def add_color():
    name = request.form.get('name', '').strip()
    if name:
        db.session.add(Color(name=name))
        db.session.commit()
        flash(f'Color "{name}" added.', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/edit_color/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_color(id):
    c = Color.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Color name cannot be empty.', 'danger')
    else:
        c.name = name
        db.session.commit()
        flash(f'Color updated to "{name}".', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/delete_color/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_color(id):
    c = Color.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash('Color deleted.', 'info')
    return redirect(url_for('products.index'))


# --- Size CRUD ---
@products_bp.route('/add_size', methods=['POST'])
@login_required
@admin_required
def add_size():
    name = request.form.get('name', '').strip()
    if name:
        db.session.add(Size(name=name))
        db.session.commit()
        flash(f'Size "{name}" added.', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/edit_size/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_size(id):
    s = Size.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Size name cannot be empty.', 'danger')
    else:
        s.name = name
        db.session.commit()
        flash(f'Size updated to "{name}".', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/delete_size/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_size(id):
    s = Size.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('Size deleted.', 'info')
    return redirect(url_for('products.index'))


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------

@products_bp.route('/variants')
@login_required
@admin_required
def variants():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    product_id = request.args.get('product_id', type=int)
    brand_id = request.args.get('brand_id', type=int)
    color_id = request.args.get('color_id', type=int)
    size_id = request.args.get('size_id', type=int)

    query = Variant.query.join(Product).join(Brand).join(Color).join(Size)

    # Powerful search — matches SKU, product name, brand, color, size
    if q:
        search = f'%{q}%'
        query = query.filter(
            db.or_(
                Variant.sku.ilike(search),
                Product.name.ilike(search),
                Brand.name.ilike(search),
                Color.name.ilike(search),
                Size.name.ilike(search),
            )
        )
    if product_id:
        query = query.filter(Variant.product_id == product_id)
    if brand_id:
        query = query.filter(Variant.brand_id == brand_id)
    if color_id:
        query = query.filter(Variant.color_id == color_id)
    if size_id:
        query = query.filter(Variant.size_id == size_id)

    variants_page = query.order_by(Variant.sku).paginate(
        page=page, per_page=50, error_out=False)

    products = Product.query.order_by(Product.name).all()
    brands = Brand.query.order_by(Brand.name).all()
    colors = Color.query.order_by(Color.name).all()
    sizes = Size.query.order_by(Size.name).all()

    return render_template('variants.html',
                           variants=variants_page,
                           products=products, brands=brands,
                           colors=colors, sizes=sizes,
                           q=q, product_id=product_id,
                           brand_id=brand_id, color_id=color_id,
                           size_id=size_id)


@products_bp.route('/variants/add', methods=['POST'])
@login_required
@admin_required
def add_variant():
    product_id = request.form.get('product_id', type=int)
    brand_id = request.form.get('brand_id', type=int)
    color_id = request.form.get('color_id', type=int)
    size_id = request.form.get('size_id', type=int)
    cost_price = request.form.get('cost_price', 0, type=float)
    selling_price = request.form.get('selling_price', 0, type=float)
    quantity = request.form.get('quantity', 0, type=int)

    product = Product.query.get(product_id)
    brand = Brand.query.get(brand_id)
    color = Color.query.get(color_id)
    size = Size.query.get(size_id)

    if not all([product, brand, color, size]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('products.variants'))

    sku = _generate_sku(product)
    variant = Variant(
        product_id=product_id, brand_id=brand_id,
        color_id=color_id, size_id=size_id,
        sku=sku, selling_price=selling_price
    )
    db.session.add(variant)
    db.session.flush()

    if quantity > 0 or cost_price > 0:
        batch = InventoryBatch(
            variant_id=variant.id,
            batch_number=1,
            cost_price=cost_price,
            selling_price=selling_price,
            quantity=quantity,
        )
        db.session.add(batch)

    db.session.commit()
    flash(f'Variant {sku} created with {quantity} units.', 'success')
    return redirect(url_for('products.variants'))


@products_bp.route('/variants/bulk_add', methods=['POST'])
@login_required
@admin_required
def bulk_add_variants():
    product_id = request.form.get('product_id', type=int)
    brand_id = request.form.get('brand_id', type=int)
    color_id = request.form.get('color_id', type=int)
    cost_price = request.form.get('cost_price', 0, type=float)
    selling_price = request.form.get('selling_price', 0, type=float)

    product = Product.query.get(product_id)
    brand = Brand.query.get(brand_id)
    color = Color.query.get(color_id)
    sizes = Size.query.order_by(Size.name).all()

    if not all([product, brand, color]):
        flash('Product, Brand, and Color are required.', 'danger')
        return redirect(url_for('products.variants'))

    created = 0
    for size in sizes:
        sku = _generate_sku(product)
        v = Variant(product_id=product_id, brand_id=brand_id,
                    color_id=color_id, size_id=size.id,
                    sku=sku, selling_price=selling_price)
        db.session.add(v)
        db.session.flush()
        db.session.add(InventoryBatch(
            variant_id=v.id, batch_number=1,
            cost_price=cost_price, selling_price=selling_price, quantity=0
        ))
        created += 1

    db.session.commit()
    flash(f'{created} variant(s) created.', 'success')
    return redirect(url_for('products.variants'))


@products_bp.route('/variants/edit/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_variant(id):
    v = Variant.query.get_or_404(id)
    cost_price = request.form.get('cost_price', type=float)
    selling_price = request.form.get('selling_price', type=float)

    if selling_price is not None:
        v.selling_price = selling_price

    # Also update the latest batch prices if they exist
    latest_batch = InventoryBatch.query.filter_by(variant_id=v.id)\
        .order_by(InventoryBatch.date_added.desc()).first()
    if latest_batch:
        if cost_price is not None:
            latest_batch.cost_price = cost_price
        if selling_price is not None:
            latest_batch.selling_price = selling_price

    db.session.commit()
    flash('Variant prices updated.', 'success')
    return redirect(url_for('products.variants'))


@products_bp.route('/variants/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_variant(id):
    v = Variant.query.get_or_404(id)
    try:
        from sqlalchemy import text
        db.session.execute(text("DELETE FROM inventory WHERE variant_id = :vid"), {'vid': v.id})
        db.session.flush()
    except Exception:
        db.session.rollback()
        v = Variant.query.get_or_404(id)
    InventoryBatch.query.filter_by(variant_id=v.id).delete()
    SaleItem.query.filter_by(variant_id=v.id).delete()
    db.session.delete(v)
    db.session.commit()
    flash('Variant deleted.', 'info')
    return redirect(url_for('products.variants'))


# ---------------------------------------------------------------------------
# AJAX — sale detail for modal
# ---------------------------------------------------------------------------

@products_bp.route('/api/sale_detail/<int:sale_id>')
@login_required
def sale_detail(sale_id):
    from models import Sale
    sale = Sale.query.get_or_404(sale_id)
    items = []
    for item in sale.items:
        items.append({
            'sku': item.variant.sku,
            'product': item.variant.product.name,
            'brand': item.variant.brand.name,
            'color': item.variant.color.name,
            'size': item.variant.size.name,
            'quantity': item.quantity,
            'cost_price': float(item.cost_price_at_sale),
            'selling_price': float(item.selling_price_at_sale),
            'profit': float(item.profit),
        })
    return jsonify({
        'id': sale.id,
        'date': sale.date.strftime('%d %b %Y %H:%M'),
        'recorded_by': sale.recorded_by or 'admin',
        'notes': sale.notes or '',
        'items': items,
        'total_revenue': sale.total_revenue(),
        'total_profit': sale.total_profit(),
    })
