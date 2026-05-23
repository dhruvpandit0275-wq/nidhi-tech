import os
import time
import random
import requests
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from queue import Queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. लॉन्च-रेडी और स्ट्रॉन्ग कॉन्फ़िगरेशन
# ==========================================
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "contactsapnaportals@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "hbwiyredkggkepgx")

# API Keys (Unlimited 100-100 Logic)
api_keys_status = {
    "651474860309": {"active": True, "name": "Primary Key (6514)", "usage": 0},
    "BKHPH3305P": {"active": True, "name": "Secondary Key (BKHPH)", "usage": 0},
    "202121": {"active": True, "name": "Admin Key", "usage": 0}
}

otp_store = {} 
server_logs = []
connection_status = {"main_portal": "Connected", "error_message": None, "solution": None}
otp_queue = Queue()

# Dynamic Site Registration
registered_sites = ["https://nidhi-tech.onrender.com", "http://127.0.0.1:5000"]

# ==========================================
# 2. ऑटो-पिंग (2 Sec Delay - Server Never Sleeps)
# ==========================================
def keep_alive_ping():
    while True:
        for site in registered_sites:
            try:
                requests.get(f"{site}/health-check", timeout=5)
            except:
                pass
        time.sleep(2)

ping_thread = threading.Thread(target=keep_alive_ping, daemon=True)
ping_thread.start()

# ==========================================
# 3. कोर फंक्शनलिटी
# ==========================================
def verify_against_storage(email, otp):
    if email in otp_store:
        data = otp_store[email]
        if time.time() < data["expires_at"] and str(data["otp"]) == str(otp):
            del otp_store[email] 
            return True
    return False

def terminal_log(status, message, details=None):
    sep = "=" * 60
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(sep)
    print(f"[{timestamp}] | STATUS: {status}")
    print(f"MESSAGE  : {message}")
    if details: print(f"DETAILS  : {details}")
    print(sep)

def log_event(status, message, error_type=None, solution=None):
    log_entry = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": status, "message": message}
    server_logs.insert(0, log_entry)
    terminal_log(status, message)

# ==========================================
# 4. मेलर इंजन (Fixed with API Integration)
# ==========================================
def send_premium_mail(target_email, otp, action_name):
    try:
        api_url = "https://api.brevo.com/v3/smtp/email"
        api_key = os.environ.get("BREVO_API_KEY")
        
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f6f9fc; padding: 30px;">
            <div style="max-width: 550px; background-color: #ffffff; margin: auto; border-top: 4px solid #2980b9; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 25px;">
                <h2 style="color: #2c3e50; text-align: center;">Nidhi Tech - Verification Service</h2>
                <p>Hello User,</p>
                <p>We received a request for <strong>{action_name}</strong> on our portal. If this was you, please use the OTP below to proceed.</p>
                
                <div style="text-align: center; margin: 30px 0; background: #ebf5fb; padding: 15px; border-radius: 6px;">
                    <span style="font-size: 36px; font-weight: bold; color: #2980b9; letter-spacing: 8px;">{otp}</span>
                </div>
                
                <p style="font-size: 14px; color: #555;"><strong>Requested Time:</strong> {current_time}</p>
                <p style="font-size: 14px; color: #555;"><strong>Service Name:</strong> {action_name}</p>
                
                <div style="margin-top: 30px; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; font-size: 13px; color: #856404;">
                    <strong>⚠️ Security Warning:</strong> This code is valid for 5 minutes only. Do not share this OTP with anyone, including Nidhi Tech support. If you did not initiate this request, please ignore this email.
                </div>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 25px 0;">
                <p style="text-align: center; font-size: 12px; color: #999;">&copy; {datetime.now().year} Nidhi Tech presented by Sapna Portals. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        payload = {
            "sender": {"email": "contactsapnaportals@gmail.com", "name": "Nidhi Tech"},
            "to": [{"email": target_email}],
            "subject": f"Security Alert: {action_name} Verification",
            "htmlContent": html_content
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"API Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to send mail. Reason: {str(e)}")
        return False

# ==========================================
# 5. API एंडपॉइंट्स
# ==========================================
@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    api_key = data.get("api_key")
    # यहाँ action को डायनामिक रखा गया है, डिफ़ॉल्ट 'Verification' रहेगा
    action = data.get("action", "Verification").capitalize() 

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    if api_key in api_keys_status and api_keys_status[api_key]["active"]:
        if api_keys_status[api_key]["usage"] < 100:
            api_keys_status[api_key]["usage"] += 1
            
            otp = str(random.randint(100000, 999999))
            otp_store[email] = {"otp": otp, "expires_at": time.time() + 300}
            
            # बिना थ्रेड के कॉल करें ताकि ईमेल पक्का जाए
            success = send_premium_mail(email, otp, action)
            
            if success:
                log_event("SUCCESS", f"{action} OTP sent to {email}")
                return jsonify({"status": "success", "message": f"{action} OTP sent successfully"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send email"}), 500
        else:
            return jsonify({"status": "error", "message": "API Key usage limit reached"}), 429
            
    return jsonify({"status": "error", "message": "Invalid API Key"}), 403

@app.route('/verifyotp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    otp = str(data.get('otp', '')).strip()
    action = data.get('action', 'Verification').capitalize()
    
    if verify_against_storage(email, otp):
        log_event("SUCCESS", f"{action} Verification Success for: {email}")
        return jsonify({"status": "success", "message": "Verified successfully"}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid or Expired OTP"}), 400

# ==========================================
# 6. ADMIN & FEEDBACK SYSTEM
# ==========================================
@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    otp = str(data.get("otp", "")).strip()
    message = data.get("message")

    if verify_against_storage(email, otp):
        server_logs.insert(0, {"type": "feedback", "email": email, "msg": message, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        log_event("SUCCESS", f"Feedback received from {email}")
        return jsonify({"status": "success", "message": "Feedback submitted successfully"})
    
    return jsonify({"status": "error", "message": "Invalid OTP. Feedback rejected."}), 400

@app.route('/admin/reply', methods=['POST'])
def admin_reply():
    data = request.json or {}
    if data.get("admin_key") == "202121":
        user_email = data.get("email")
        reply_msg = data.get("reply")
        
        # यहाँ भी थ्रेड हटा दिया गया है ताकि ईमेल जाने तक रिस्पॉन्स रुके रहे
        success = send_premium_mail(user_email, reply_msg, "Admin Support Reply")
        
        if success:
            return jsonify({"status": "success", "message": "Reply sent to user"})
        else:
            return jsonify({"status": "error", "message": "Failed to send email"}), 500
            
    return jsonify({"error": "Unauthorized"}), 403

@app.route('/health-check', methods=['GET'])
def health_check(): return jsonify({"status": "alive"}), 200

@app.route('/dashboard', methods=['GET'])
def dashboard_view():
    return render_template('dashboard.html', api_keys=api_keys_status, logs=server_logs, sites=registered_sites)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
