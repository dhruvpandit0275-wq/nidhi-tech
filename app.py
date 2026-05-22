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
    "202121": {"active": True, "name": "Admin Key", "usage": 0} # <--- क्या यह की यहाँ है?
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
        time.sleep(2) # 2 Second interval for constant wake

ping_thread = threading.Thread(target=keep_alive_ping, daemon=True)
ping_thread.start()

# ==========================================
# 3. कोर फंक्शनलिटी (पुराना कोड सुरक्षित)
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
# 4. मेलर इंजन (Premium)
# ==========================================
def send_premium_mail(target_email, otp, action_name):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔒 Security Alert: Your {action_name} Verification Code"
        msg['From'] = f"Nidhi Tech ( Sapna Portals ) <{SMTP_EMAIL}>"
        msg['To'] = target_email
        html_content = f"<html><body><h1 style='color:blue;'>OTP: {otp}</h1><p>Valid for 5 mins.</p></body></html>"
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, target_email, msg.as_string())
        server.quit()
        return True
    except:
        return False

# ==========================================
# 5. API एंडपॉइंट्स (Updated with Unlimited 100/100 Logic)
# ==========================================
@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json or {}
    
    # 1. ईमेल को हमेशा lowercase में लें ताकि वेरिफिकेशन एरर न आए
    email = data.get("email", "").strip().lower()
    api_key = data.get("api_key")
    action = data.get("action", "Verification")

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    # 2. Key Validation
    if api_key in api_keys_status and api_keys_status[api_key]["active"]:
        
        # 3. Unlimited/Reset-able Limit Logic (100 limit check)
        if api_keys_status[api_key]["usage"] < 100:
            api_keys_status[api_key]["usage"] += 1
            
            # OTP Generation
            otp = str(random.randint(100000, 999999))
            # डेटा सेव करें
            otp_store[email] = {
                "otp": otp, 
                "expires_at": time.time() + 300
            }
            
            # 4. Mailer Call
            if send_premium_mail(email, otp, action):
                log_event("SUCCESS", f"OTP Sent to {email} using {api_keys_status[api_key]['name']}")
                return jsonify({"status": "success", "message": "OTP sent successfully"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send mail"}), 500
        else:
            # अगर लिमिट खत्म हो गई है
            log_event("LIMIT_REACHED", f"Key {api_key} limit reached.")
            return jsonify({"status": "error", "message": "API Key usage limit reached (100/100). Please rotate key."}), 429
            
    return jsonify({"status": "error", "message": "Invalid API Key provided"}), 403

@app.route('/verifyotp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    otp = str(data.get('otp', '')).strip()

    # DEBUG: सर्वर में क्या मौजूद है ये देखें
    print(f"DEBUG: Verifying {email}. Current store keys: {list(otp_store.keys())}")
    
    # वेरिफिकेशन कॉल करें
    if verify_against_storage(email, otp):
        log_event("SUCCESS", f"Verification Success for: {email}")
        return jsonify({"status": "success", "message": "Verified"}), 200
    else:
        # अगर डेटा नहीं मिला, तो ये लॉग्स आपको असली कारण बताएंगे
        log_event("FAILED", f"Verification Failed for: {email}. Supplied OTP: {otp}")
        print(f"DEBUG: Failed OTP Store data for {email}: {otp_store.get(email)}")
        
        return jsonify({
            "status": "error", 
            "message": "Invalid or Expired OTP"
        }), 400

# ==========================================
# 6. ADMIN & FEEDBACK SYSTEM (NEW)
# ==========================================
@app.route('/admin/add-site', methods=['POST'])
def add_site():
    data = request.json
    if data.get("admin_key") == ADMIN_API_KEY:
        registered_sites.append(data.get("url"))
        return jsonify({"status": "Site added successfully"})
    return jsonify({"error": "Unauthorized"}), 403

# ओटीपी वेरिफिकेशन के बाद ही फीडबैक स्वीकार करने वाला रूट
@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    otp = str(data.get("otp", "")).strip()
    message = data.get("message")

    # पहले ओटीपी वेरीफाई करें
    if verify_against_storage(email, otp):
        # अगर ओटीपी सही है, तभी फीडबैक सेव करें
        server_logs.insert(0, {
            "type": "feedback", 
            "email": email, 
            "msg": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        log_event("SUCCESS", f"Feedback received from {email}")
        return jsonify({"status": "success", "message": "Feedback submitted successfully"})
    else:
        # अगर ओटीपी गलत है या एक्सपायर हो गया है
        return jsonify({"status": "error", "message": "Invalid OTP. Feedback rejected."}), 400

@app.route('/admin/reply', methods=['POST'])
def admin_reply():
    data = request.json
    if data.get("admin_key") == "202121": # Admin Auth
        user_email = data.get("email")
        reply_msg = data.get("reply")
        
        # मेल भेजने का लॉजिक
        send_premium_mail(user_email, reply_msg, "Admin Support Reply")
        return jsonify({"status": "success"})
    return jsonify({"error": "Unauthorized"}), 403

@app.route('/health-check', methods=['GET'])
def health_check():
    return jsonify({"status": "alive"}), 200

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return '', 204

@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('dashboard_view'))

@app.route('/dashboard', methods=['GET'])
def dashboard_view():
    return render_template('dashboard.html', api_keys=api_keys_status, logs=server_logs, sites=registered_sites)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)