# modules/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import db, User
from sqlalchemy.exc import IntegrityError
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Add this to the login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email  # Make sure this line is present
            session.permanent = True
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
        return redirect(url_for('auth.login'))

    return render_template('auth.html', action="Login")

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    # Clear any existing session when accessing signup page
    session.clear()
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([name, email, password]):
            flash('All fields are required', 'error')
            return render_template('auth.html', action="Sign Up")
        
        # Check if email already exists before trying to create user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('auth.html', action="Sign Up")
        
        try:
            new_user = User(name=name, email=email)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('auth.html', action="Sign Up")
            
    return render_template('auth.html', action="Sign Up")

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

# Add this new route after your existing routes
# Change the route name to match the template
@auth_bp.route('/profile-update', methods=['POST'])
@login_required
def profile_update():
    try:
        user = User.query.get(session['user_id'])
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('settings.settings_page'))
        
        name = request.form.get('name')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        # Update name and email if provided
        if name:
            user.name = name
        if email and email != user.email:
            # Check if email is already taken
            if User.query.filter_by(email=email).first():
                flash('Email already in use', 'error')
                return redirect(url_for('settings.settings_page'))
            user.email = email
        
        # Update password if provided
        if current_password and new_password:
            if not user.check_password(current_password):
                flash('Current password is incorrect', 'error')
                return redirect(url_for('settings.settings_page'))
            user.set_password(new_password)
            flash('Password updated successfully', 'success')
        
        db.session.commit()
        session['user_name'] = user.name  # Update session with new name
        session['user_email'] = user.email  # Update session with new email
        flash('Profile updated successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'error')
        print(f"Error updating profile: {str(e)}")
    
    return redirect(url_for('settings.settings_page'))