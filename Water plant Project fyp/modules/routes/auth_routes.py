# modules/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import db, User
from sqlalchemy.exc import IntegrityError
from functools import wraps
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

# Dictionary to store OTPs and their expiration times
otp_store = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to generate a random OTP
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


# Function to send OTP via email
def send_otp_email(email, otp):
    try:

        # Configure these settings with your email provider details
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "mohasim541@gmail.com"  # Replace with your email
        sender_password = "ieco nxai mbkr yoeu"  # Replace with your app password
        
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = email
        message["Subject"] = "Your Verification Code for Predictive Maintenance System"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Email Verification</h2>
            <p>Thank you for signing up with our Predictive Maintenance System!</p>
            <p>Your verification code is: <strong>{otp}</strong></p>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
        </body>
        </html>
        """
        
        # Add HTML content
        message.attach(MIMEText(body, "html"))
        
        # Connect to server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

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
            # Check if user is verified
            if not user.is_verified:
                flash('Please verify your email before logging in', 'error')
                return redirect(url_for('auth.verify_email', email=email))
                
            session.clear()
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email
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
        
        # Validate email format
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth.html', action="Sign Up")
        
        # Validate password length
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('auth.html', action="Sign Up")
        
        # Check if email already exists before trying to create user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('auth.html', action="Sign Up")
        
        try:
            # Create user with verified=False
            new_user = User(name=name, email=email, is_verified=False)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Generate and store OTP
            otp = generate_otp()
            expiry_time = datetime.now() + timedelta(minutes=10)
            otp_store[email] = {
                'otp': otp,
                'expiry': expiry_time,
                'user_id': new_user.id
            }
            
            # Send OTP email
            if send_otp_email(email, otp):
                flash('Account created! Please check your email for verification code.', 'success')
                return redirect(url_for('auth.verify_email', email=email))
            else:
                flash('Failed to send verification email. Please try again.', 'error')
                # Delete the user if email sending fails
                db.session.delete(new_user)
                db.session.commit()
                return render_template('auth.html', action="Sign Up")
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('auth.html', action="Sign Up")
            
    return render_template('auth.html', action="Sign Up")

@auth_bp.route('/verify-email/<email>', methods=['GET', 'POST'])
def verify_email(email):
    # If OTP for this email doesn't exist, redirect to signup
    if email not in otp_store:
        flash('Verification session expired. Please sign up again.', 'error')
        return redirect(url_for('auth.signup'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        
        # Check if OTP is valid and not expired
        if datetime.now() > otp_store[email]['expiry']:
            # OTP expired
            del otp_store[email]
            flash('Verification code expired. Please sign up again.', 'error')
            return redirect(url_for('auth.signup'))
        
        if entered_otp == otp_store[email]['otp']:
            # OTP is correct, mark user as verified
            user_id = otp_store[email]['user_id']
            user = User.query.get(user_id)
            
            if user:
                user.is_verified = True
                db.session.commit()
                
                # Clean up OTP store
                del otp_store[email]
                
                flash('Email verified successfully! You can now login.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('User not found. Please sign up again.', 'error')
                return redirect(url_for('auth.signup'))
        else:
            flash('Invalid verification code. Please try again.', 'error')
    
    return render_template('verify_email.html', email=email)

@auth_bp.route('/resend-otp/<email>')
def resend_otp(email):
    # Check if user exists
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash('Email not found. Please sign up first.', 'error')
        return redirect(url_for('auth.signup'))
    
    # Generate new OTP
    otp = generate_otp()
    expiry_time = datetime.now() + timedelta(minutes=10)
    otp_store[email] = {
        'otp': otp,
        'expiry': expiry_time,
        'user_id': user.id
    }
    
    # Send OTP email
    if send_otp_email(email, otp):
        flash('Verification code resent. Please check your email.', 'success')
    else:
        flash('Failed to send verification email. Please try again.', 'error')
    
    return redirect(url_for('auth.verify_email', email=email))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

# Profile update route
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