"""Authentication — login, logout, change password, manage staff accounts."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from models import db, User

auth_bp = Blueprint('auth', __name__)


def admin_required(f):
    """Decorator — restricts route to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_staff():
            return redirect(url_for('staff.sales'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            if user.is_staff():
                return redirect(url_for('staff.sales'))
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_username = request.form.get('new_username', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.change_password'))
        if len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'danger')
            return redirect(url_for('auth.change_password'))
        if not new_username:
            flash('Username cannot be empty.', 'danger')
            return redirect(url_for('auth.change_password'))

        existing = User.query.filter_by(username=new_username).first()
        if existing and existing.id != current_user.id:
            flash('That username is already taken.', 'danger')
            return redirect(url_for('auth.change_password'))

        current_user.username = new_username
        current_user.set_password(new_password)
        db.session.commit()
        flash('Credentials updated. Please log in again.', 'success')
        logout_user()
        return redirect(url_for('auth.login'))

    return render_template('change_password.html')


# ---------------------------------------------------------------------------
# Staff Management (admin only)
# ---------------------------------------------------------------------------

@auth_bp.route('/staff')
@login_required
@admin_required
def staff_list():
    """Show all staff accounts."""
    staff = User.query.filter_by(role='staff').order_by(User.username).all()
    return render_template('staff_manage.html', staff=staff)


@auth_bp.route('/staff/add', methods=['POST'])
@login_required
@admin_required
def add_staff():
    """Create a new staff account."""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('auth.staff_list'))
    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('auth.staff_list'))
    if User.query.filter_by(username=username).first():
        flash(f'Username "{username}" is already taken.', 'danger')
        return redirect(url_for('auth.staff_list'))

    staff = User(username=username, role='staff')
    staff.set_password(password)
    db.session.add(staff)
    db.session.commit()
    flash(f'Staff account "{username}" created.', 'success')
    return redirect(url_for('auth.staff_list'))


@auth_bp.route('/staff/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_staff(id):
    """Delete a staff account."""
    staff = User.query.get_or_404(id)
    if staff.is_admin():
        flash('Cannot delete an admin account.', 'danger')
        return redirect(url_for('auth.staff_list'))
    db.session.delete(staff)
    db.session.commit()
    flash('Staff account deleted.', 'info')
    return redirect(url_for('auth.staff_list'))


@auth_bp.route('/staff/reset/<int:id>', methods=['POST'])
@login_required
@admin_required
def reset_staff_password(id):
    """Reset a staff member's password."""
    staff = User.query.get_or_404(id)
    new_password = request.form.get('new_password', '')
    if len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('auth.staff_list'))
    staff.set_password(new_password)
    db.session.commit()
    flash(f'Password for "{staff.username}" has been reset.', 'success')
    return redirect(url_for('auth.staff_list'))
