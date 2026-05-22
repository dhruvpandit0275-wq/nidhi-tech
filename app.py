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
# 4. मेलर इंजन (Fixed with Async Threading)
# ==========================================
def send_premium_mail(target_email, otp, action_name):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔒 Security Alert: Your {action_name} Verification Code"
        msg['From'] = f"Nidhi Tech ( Sapna Portals ) <{SMTP_EMAIL}>"
        msg['To'] = target_email
        html_content = f"<html><body><h1 style='color:blue;'>OTP: {otp}</h1><p>Valid for 5 mins.</p></body></html>"
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, target_email, msg.as_string())
        server.quit()
        return True
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
    action = data.get("action", "Verification")

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    if api_key in api_keys_status and api_keys_status[api_key]["active"]:
        if api_keys_status[api_key]["usage"] < 100:
            api_keys_status[api_key]["usage"] += 1
            
            otp = str(random.randint(100000, 999999))
            otp_store[email] = {"otp": otp, "expires_at": time.time() + 300}
            
            # Threading का उपयोग ताकि रिस्पॉन्स फास्ट मिले
            thread = threading.Thread(target=send_premium_mail, args=(email, otp, action))
            thread.start()
            
            log_event("SUCCESS", f"OTP Process started for {email}")
            return jsonify({"status": "success", "message": "OTP sent successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "API Key usage limit reached (100/100)"}), 429
            
    return jsonify({"status": "error", "message": "Invalid API Key"}), 403

@app.route('/verifyotp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    otp = str(data.get('otp', '')).strip()
    
    if verify_against_storage(email, otp):
        log_event("SUCCESS", f"Verification Success for: {email}")
        return jsonify({"status": "success", "message": "Verified"}), 200
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
    data = request.json
    if data.get("admin_key") == "202121":
        user_email = data.get("email")
        reply_msg = data.get("reply")
        thread = threading.Thread(target=send_premium_mail, args=(user_email, reply_msg, "Admin Support Reply"))
        thread.start()
        return jsonify({"status": "success"})
    return jsonify({"error": "Unauthorized"}), 403

@app.route('/health-check', methods=['GET'])
def health_check(): return jsonify({"status": "alive"}), 200

@app.route('/dashboard', methods=['GET'])
def dashboard_view():
    return render_template('dashboard.html', api_keys=api_keys_status, logs=server_logs, sites=registered_sites)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
