import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

def load_config():
    """Load configuration from config.json file"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

class NotificationManager:
    def __init__(self):
        """Initialize notification manager with settings from config"""
        config = load_config()
        
        # Email settings
        self.email_sender = config.get('notification_email_sender', '')
        self.email_password = config.get('notification_email_password', '')
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        
        # Notification settings - Fix the swapped settings
        self.failure_emails_enabled = config.get('notify_failures', True)
        self.warning_emails_enabled = config.get('notify_warnings', True)
        print("send email")
        # Cooldown tracking
        self.last_notification = {
            'A1': {'failure': None, 'warning': None},
            'A2': {'failure': None, 'warning': None},
            'A3': {'failure': None, 'warning': None},
            'A4': {'failure': None, 'warning': None}
        }
    
    def should_send_notification(self, asset_id, prediction):
        """Check if notification should be sent based on cooldown and settings"""
        now = datetime.now()
        is_failure = prediction.get('failure_predicted') == 1
        probability = prediction.get('failure_probability', 0)
        
        # Load config to get gauge thresholds
        config = load_config()
        gauges = config.get('gauges', [])
        
        # Determine notification type
        if is_failure and self.failure_emails_enabled:
            notification_type = 'failure'
            # Check if we've sent a failure notification in the last 12 hours
            last_sent = self.last_notification[asset_id]['failure']
            cooldown = timedelta(hours=12)
            print(f"Failure detected for {asset_id}, checking if notification should be sent")
        elif not is_failure and self.warning_emails_enabled:
            # For warnings, check if any gauge is above its warning threshold
            # Map asset IDs to their corresponding gauge keys
            asset_gauge_mapping = {
                'A1': ['DHT11.humidity_percent', 'DHT11.temperature_C'],
                'A2': ['DS18B20.temperature_C'],
                'A3': ['Ultrasonic.distance_cm'],
                'A4': ['FlowSensor.flowRate_Lmin']
            }
            
            # Get the gauge keys for this asset
            gauge_keys = asset_gauge_mapping.get(asset_id, [])
            
            # Check if any gauge for this asset is in warning state
            warning_triggered = False
            warning_gauge = None
            
            for gauge in gauges:
                value_key = gauge.get('value_key')
                if value_key in gauge_keys:
                    warning_threshold = gauge.get('warning_threshold')
                    # Get the current value from sensor data (if available)
                    # This would need to be passed in or retrieved
                    # For now, we'll use probability as a proxy
                    if probability * 100 > warning_threshold:
                        warning_triggered = True
                        warning_gauge = gauge
                        break
            
            if warning_triggered:
                notification_type = 'warning'
                print("Warning email sending")
                # Check if we've sent a warning notification in the last hour
                last_sent = self.last_notification[asset_id]['warning']
                cooldown = timedelta(hours=1)
                print(f"Warning threshold exceeded for {asset_id} on gauge {warning_gauge.get('title')}")
            else:
                # No warning threshold exceeded
                print(f"No warning thresholds exceeded for {asset_id}")
                return False, None
        else:
            # No notification needed
            print(f"No notification needed (conditions not met)")
            return False, None
        
        # Check cooldown
        if last_sent and (now - last_sent) < cooldown:
           
            return False, notification_type
        
        # Update last notification time
        self.last_notification[asset_id][notification_type] = now
        return True, notification_type
    
    def send_email_notification(self, asset_id, prediction, notification_type):
        """Send email notification for asset failure or warning"""
        config = load_config()
        recipient_email = config.get('notification_email')
        
        if not recipient_email:
            print("No recipient email configured, skipping notification")
            return False
            
        # Get asset name based on asset ID
        asset_names = {
            'A1': 'Air Temperature & Humidity System',
            'A2': 'Water Temperature System',
            'A3': 'Ultrasonic Distance System',
            'A4': 'Water Flow System'
        }
        
        asset_name = asset_names.get(asset_id, f"Asset {asset_id}")
        probability = prediction.get('failure_probability', 0) * 100
        timestamp = prediction.get('timestamp', datetime.now().isoformat())
        
        # Format timestamp for display
        try:
            dt = datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = timestamp
            
        # Create email subject and body based on notification type
        if notification_type == "failure":
            subject = f"ALERT: Failure Predicted for {asset_name}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
                    <h2 style="color: #d32f2f; margin-bottom: 20px;">⚠️ Failure Prediction Alert</h2>
                    <p>A potential failure has been predicted for <strong>{asset_name}</strong>.</p>
                    <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p><strong>Asset ID:</strong> {asset_id}</p>
                        <p><strong>Failure Probability:</strong> {probability:.2f}%</p>
                        <p><strong>Prediction Time:</strong> {formatted_time}</p>
                    </div>
                    <p>Please take immediate action to investigate this issue and prevent potential system failure.</p>
                    <p style="margin-top: 30px; font-size: 0.9em; color: #757575;">This is an automated message from your Water Plant Monitoring System.</p>
                </div>
            </body>
            </html>
            """
        else:  # warning
            subject = f"Warning: Elevated Risk for {asset_name}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
                    <h2 style="color: #ff9800; margin-bottom: 20px;">⚠️ Warning Alert</h2>
                    <p>An elevated risk level has been detected for <strong>{asset_name}</strong>.</p>
                    <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p><strong>Asset ID:</strong> {asset_id}</p>
                        <p><strong>Failure Probability:</strong> {probability:.2f}%</p>
                        <p><strong>Prediction Time:</strong> {formatted_time}</p>
                    </div>
                    <p>Please monitor this asset closely and consider preventive maintenance if conditions worsen.</p>
                    <p style="margin-top: 30px; font-size: 0.9em; color: #757575;">This is an automated message from your Water Plant Monitoring System.</p>
                </div>
            </body>
            </html>
            """
            
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_sender
        msg['To'] = recipient_email
        
        # Attach HTML content
        msg.attach(MIMEText(body, 'html'))
        
        try:
            # Connect to SMTP server and send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            
            print(f"Notification email sent for {asset_id} ({notification_type})")
            return True
        except Exception as e:
            print(f"Failed to send notification email: {e}")
            return False