from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
import json
import os

# Change the Blueprint name to 'settings' to match what's being imported
settings = Blueprint('settings', __name__)

# Path to the config file
# Update the CONFIG_FILE path to be absolute
CONFIG_FILE = 'c:/Users/DELL/Desktop/my fyp ml/Water plant Project fyp/config.json'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'notification_email': '',
        'notify_failures': True,
        'notify_warnings': True,
        'warning_threshold': 50
    }

def save_config(config):
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        # Save with proper encoding and formatting
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
    except PermissionError:
        raise Exception("Permission denied. Cannot save to config file.")
    except Exception as e:
        raise Exception(f"Failed to save settings: {str(e)}")

@settings.route('/settings/save', methods=['POST'])
@login_required
def save_settings():
    try:
        config = load_config()
        
        # Update notification email
        notification_email = request.form.get('notification_email')
        if notification_email:
            config['notification_email'] = notification_email.strip()
        
        # Update notification preferences
        config['notify_failures'] = 'notify_failures' in request.form
        config['notify_warnings'] = 'notify_warnings' in request.form
        
        # Update warning threshold with validation
        warning_threshold = request.form.get('warning_threshold')
        if warning_threshold and warning_threshold.isdigit():
            threshold = int(warning_threshold)
            if 1 <= threshold <= 99:
                config['warning_threshold'] = threshold
            else:
                flash('Warning threshold must be between 1 and 99', 'error')
                return redirect(url_for('settings.settings_page'))
        
        # Save the updated config
        save_config(config)
        flash('Settings saved successfully', 'success')
        
    except Exception as e:
        flash(f'Error saving settings: {str(e)}', 'error')
        print(f"Settings save error: {str(e)}")  # For debugging
        
    return redirect(url_for('settings.settings_page'))

# Update all route decorators to use 'settings' instead of 'settings_bp'
@settings.route('/settings')
@login_required
def settings_page():
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        config = {
            'notification_email': '',
            'notify_failures': True,
            'notify_warnings': True,
            'warning_threshold': 50
        }
        flash('Error loading settings. Using default values.', 'error')
    
    return render_template('settings.html', config=config, active_page='settings')
