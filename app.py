import os
import time
import random
import requests
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from queue import Queue

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. लॉन्च-रेडी कॉन्फ़िगरेशन
# ==========================================
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "contactsapnaportals@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "hbwiyredkggkepgx")
api_keys_status = {
    "651474860309": {"active": True, "name": "Primary Key (6514)"},
    "BKHPH3305P": {"active": True, "name": "Secondary Key (BKHPH)"}
}

otp_store = {}        
server_logs = []      
connection_status = {"main_portal": "Connected", "error_message": None, "solution": None}
otp_queue = Queue() # 3-4 रिक्वेस्ट एक साथ आने पर क्रैश रोकने के लिए

# ==========================================
# 2. कोर फंक्शनलिटी: वेरिफिकेशन और लॉगिंग
# ==========================================
def verify_against_storage(email, otp):
    if email in otp_store:
        data = otp_store[email]
        if time.time() < data["expires_at"] and str(data["otp"]) == str(otp):
            # वेरिफिकेशन के बाद ओटीपी डिलीट करना ताकि रीयूज न हो
            del otp_store[email] 
            return True
    return False

def terminal_log(status, message, details=None):
    sep = "=" * 60
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(sep)
    print(f"[{timestamp}] | STATUS: {status}")
    print(f"MESSAGE  : {message}")
    if details:
        print(f"DETAILS  : {details}")
    print(sep)

def log_event(status, message, error_type=None, solution=None):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "message": message,
        "error_type": error_type,
        "solution": solution
    }
    server_logs.insert(0, log_entry)
    combined_details = f"Err: {error_type} | Fix: {solution}" if error_type else None
    terminal_log(status, message, combined_details)

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return '', 204

# ==========================================
# 3. बैकग्राउंड सेल्फ-पिंग
# ==========================================
def keep_alive_ping():
    session = requests.Session()
    while True:
        time.sleep(25)  
        try:
            session.get("http://127.0.0.1:5000/health-check", timeout=5)
        except Exception:
            pass

ping_thread = threading.Thread(target=keep_alive_ping, daemon=True)
ping_thread.start()

@app.route('/health-check', methods=['GET'])
def health_check():
    return jsonify({"status": "alive", "timestamp": str(datetime.now())}), 200

# ==========================================
# 4. मेलर इंजन
# ==========================================
def send_premium_mail(target_email, otp, action_name):
    import smtplib
    import datetime
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # टाइम और डेट जनरेट करना
    current_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S IST")
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🔒 Security Alert: Your {action_name} Verification Code"
    msg['From'] = f"Nidhi Tech ( Sapna Portals ) <{SMTP_EMAIL}>"
    msg['To'] = target_email
    
    # प्रीमियम और इंफॉर्मेटिव HTML कंटेंट
    html_content = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #334155;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 12px; border-top: 5px solid #0056b3; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h2 style="color: #0056b3; text-align: center;">NIDHI TECH - SAPNA PORTALS</h2>
            <p>Dear User,</p>
            <p>You have requested a secure verification code for <strong>{action_name}</strong>.</p>
            
            <div style="background-color: #f1f5f9; padding: 20px; text-align: center; border-radius: 8px; margin: 25px 0;">
                <p style="margin: 0; font-size: 14px;">Your One-Time Password (OTP) is:</p>
                <h1 style="color: #1e293b; font-size: 36px; margin: 10px 0; letter-spacing: 5px;">{otp}</h1>
                <p style="margin: 0; font-size: 12px; color: #64748b;">This code expires in 5 minutes.</p>
            </div>

            <div style="font-size: 13px; color: #475569; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                <p><strong>Request Details:</strong></p>
                <ul style="padding-left: 20px;">
                    <li><strong>Date/Time:</strong> {current_time}</li>
                    <li><strong>Support Mail:</strong>nidhibankingpoint@gmail.com</li>
                    <li><strong>Contact Number:</strong>9084216689</li>
                    <li><strong>Support Hours:</strong>Monday To Saturday 10am To 6pm </li>
                </ul>
                <p style="color: #dc3545;"><strong>⚠️ Security Warning:</strong> If you did not initiate this request, please ignore this email or contact support immediately. Do not share this OTP with anyone.</p>
            </div>
            
            <p style="text-align: center; font-size: 11px; color: #94a3b8; margin-top: 30px;">
                © 2026 Nidhi Tech presented by Sapna Portals. All rights reserved.
            </p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        # स्पैम से बचने के लिए smtp कनेक्शन को ऑप्टिमाइज़ किया है
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, target_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        log_event("FAILED", f"Email send failed: {str(e)}")
        return False

# ==========================================
# 5. API एंडपॉइंट्स (Send & Verify)
# ==========================================
@app.route('/sendotp', methods=['POST'])
@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json or {}
    email = data.get("email")
    api_key = data.get("api_key")
    action = data.get("action", "General Verification")

    if api_key not in api_keys_status or not api_keys_status[api_key]["active"]:
        return jsonify({"status": "error", "message": "Invalid API Key"}), 403

    otp = str(random.randint(100000, 999999))
    otp_store[email] = {"otp": otp, "expires_at": time.time() + 300, "action": action}

    if send_premium_mail(email, otp, action):
        log_event("SUCCESS", f"OTP ({otp}) sent to {email}")
        return jsonify({"status": "success", "message": "OTP sent"}), 200
    return jsonify({"status": "error", "message": "Server error"}), 500

@app.route('/verifyotp', methods=['POST'])
def verify_otp():
    # डेटा सुरक्षित रूप से प्राप्त करें
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    # ओटीपी को स्ट्रिंग में बदलें ताकि तुलना में कोई एरर न आए
    otp = str(data.get('otp', '')).strip()

    # सर्वर-साइड वेरिफिकेशन (Primary)
    # verify_against_storage फंक्शन अब स्ट्रिंग तुलना करेगा
    if verify_against_storage(email, otp):
        log_event("SUCCESS", f"Verification Success: {email}")
        return jsonify({"status": "success", "message": "Verified"}), 200
    else:
        # अगर सर्वर वेरिफिकेशन फेल होता है, तो Firebase के लिए 'firebase_fallback' भेजें
        log_event("FAILED", f"Verification Failed for {email}. Triggering Fallback.")
        return jsonify({
            "status": "error", 
            "message": "Invalid OTP", 
            "fallback": "firebase"
        }), 400

@app.route('/toggle_key/<key>', methods=['POST'])
def toggle_key(key):
    if key in api_keys_status:
        api_keys_status[key]["active"] = not api_keys_status[key]["active"]
    return jsonify({"status": "success"})

@app.route('/dashboard', methods=['GET'])
def dashboard_view():
    return render_template('dashboard.html', api_keys_status=api_keys_status, server_logs=server_logs, connection_status=connection_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)