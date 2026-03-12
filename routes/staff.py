"""Staff blueprint — restricted sales-only view for staff accounts."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Variant, Product, Brand, Color, Size

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


@staff_bp.route('/sales', methods=['GET'])
@login_required
def sales():
    """Staff landing page — redirect to shared new_sale route."""
    # Admins can also visit this but it just goes to new sale
    variants = (Variant.query
                .join(Product).join(Brand).join(Color).join(Size)
                .all())
    variants = [v for v in variants if v.total_stock() > 0]
    return render_template('staff_sales.html', variants=variants)
