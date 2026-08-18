import os
import time
import random
import requests
import threading
import base64
from datetime import datetime
from datetime import timedelta
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
        
        ist_now = datetime.now() + timedelta(hours=5, minutes=30)
        current_time = ist_now.strftime("%d-%m-%Y %I:%M %p")
        
        user_name = target_email.split('@')[0].replace('.', ' ').title()
        
        html_content = f"""<html>
<head>
<meta charset="UTF-8">
<style>
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #eef2f7; margin: 0; padding: 0; }}
.email-wrapper {{ width: 100%; table-layout: fixed; background-color: #eef2f7; padding: 40px 0; }}
.email-content {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); overflow: hidden; border-top: 5px solid #1abc9c; }}
.email-header {{ background: linear-gradient(135deg, #2c3e50, #1a252f); padding: 30px; text-align: center; color: #ffffff; }}
.email-header h1 {{ margin: 0; font-size: 24px; letter-spacing: 1px; color: #ffffff; }}
.email-body {{ padding: 35px 30px; color: #333333; line-height: 1.6; }}
.otp-box {{ text-align: center; margin: 30px 0; background: #e8f8f5; border: 2px dashed #1abc9c; padding: 20px; border-radius: 8px; }}
.otp-code {{ font-size: 38px; font-weight: 800; color: #16a085; letter-spacing: 10px; }}
.info-box {{ background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; font-size: 14px; color: #555555; border-radius: 4px; }}
.warning-box {{ background-color: #fef9e7; border-left: 4px solid #f1c40f; padding: 15px; margin: 20px 0; font-size: 13px; color: #7d6608; border-radius: 4px; }}
.email-footer {{ background-color: #f4f6f7; padding: 20px 30px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #e1e8ed; }}
.email-footer a {{ color: #1abc9c; text-decoration: none; }}
</style>
</head>
<body>
<center class="email-wrapper">
<table class="email-content" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td class="email-header">
<h1>Apna Nidhi Tech</h1>
<p style="margin: 5px 0 0 0; font-size: 13px; color: #bdc3c7;">A Empire Of Sapna Portals</p>
</td>
</tr>
<tr>
<td class="email-body">
<p style="font-size: 16px; margin-top: 0;">Hello <strong>{user_name}</strong>,</p>
<p style="font-size: 15px; color: #2c3e50;">You have requested an OTP for: <strong>{action_name}</strong></p>
<p>Please use the secure One-Time Password (OTP) below to complete your action.</p>
<div class="otp-box">
<span class="otp-code">{otp}</span>
</div>
<div class="info-box">
<p style="margin: 0;"><strong>Requested Time:</strong> {current_time}</p>
</div>
<div class="warning-box">
<strong>⚠️ Security Notice:</strong> This OTP is valid for 5 minutes only. Do not share this code with anyone. Nidhi Tech support will never ask for your OTP.
</div>
<p style="margin-bottom: 0; font-size: 14px;">If you face any issues or did not request this, please contact us immediately at <a href="mailto:contactsapnaportals@gmail.com" style="color: #1abc9c; font-weight: bold;">contactsapnaportals@gmail.com</a>.</p>
</td>
</tr>
<tr>
<td class="email-footer">
<p style="margin: 0;">&copy; {datetime.now().year} Apna Nidhi Tech. All rights reserved.</p>
</td>
</tr>
</table>
</center>
</body>
</html>"""
        
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

@app.route('/admin/send_otp', methods=['POST'])
def admin_send_otp():
    data = request.json or {}
    admin_key = data.get("admin_key")
    # आपने दी हुई ईमेल आईडी यहाँ सेट की गई है
    email = "dhruvpandit027@gmail.com" 

    if admin_key == "202121":
        otp = str(random.randint(100000, 999999))
        otp_store[email] = {"otp": otp, "expires_at": time.time() + 300}
        
        # एडमिन के लिए ओटीपी भेजें
        success = send_premium_mail(email, otp, "Admin Login")
        
        if success:
            log_event("SUCCESS", f"Admin OTP sent to {email}")
            return jsonify({"status": "success", "message": "Admin OTP sent successfully"})
        return jsonify({"status": "error", "message": "Failed to send email"}), 500
    
    return jsonify({"status": "error", "message": "Invalid Admin Key"}), 403


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

# (नोट: यह आपके मौजूदा ऐप का हिस्सा है, यहाँ केवल रूट और फंक्शन दिया गया है)
def send_order_email_background(payload, headers, identifier, name, service_type):
    try:
        api_url = "https://api.brevo.com/v3/smtp/email"
        response = requests.post(api_url, json=payload, headers=headers, timeout=25)
        if response.status_code in [200, 201]:
            print(f"SUCCESS: Request {identifier} ({service_type}) emailed successfully for {name}")
        else:
            print(f"Brevo API Background Error: {response.text}")
    except Exception as e:
        print(f"Background Email Error: {str(e)}")

@app.route('/submit-support', methods=['POST'])
@app.route('/submit-pvc-order', methods=['POST'])
@app.route('/submit-universal-form', methods=['POST'])
def handle_advanced_universal_submission():
    try:
        # 1. बेसिक यूजर डेटा कैप्चर (हर फॉर्म के लिए कॉमन)
        name = request.form.get('name', 'N/A')
        mobile = request.form.get('mobile', request.form.get('phone', 'N/A'))
        secondary_mobile = request.form.get('secondary_mobile', 'N/A')
        user_email = request.form.get('email', 'N/A')
        username = request.form.get('username', 'N/A')
        
        # 2. फॉर्म टाइप और सर्विस टाइप को अलग-भाग में पहचानना (मिक्सअप रोकने के लिए)
        form_source = request.form.get('form_source', 'General Portal') # जैसे: Support, PVC Order, Voter List आदि
        service_type = request.form.get('service_type', request.form.get('type', 'Standard Request')).strip()
        query_text = request.form.get('query', request.form.get('message', request.form.get('description', 'N/A')))
        custom_order_id = request.form.get('order_id', '')

        # स्मार्ट आईडी जनरेशन
        if custom_order_id:
            identifier = custom_order_id
        else:
            prefix = "SUP" if "support" in request.path.lower() else "APP"
            identifier = f"{prefix}-{random.randint(100000, 999999)}"

        # 3. डायनेमिक और एक्सटेंडेबल एड्रेस / अन्य फील्ड्स (बिना किसी एरर के)
        extra_fields = {}
        for key, value in request.form.items():
            if key not in ['name', 'mobile', 'phone', 'secondary_mobile', 'email', 'username', 'form_source', 'service_type', 'type', 'query', 'message', 'description', 'order_id', 'target_email']:
                extra_fields[key.replace('_', ' ').title()] = value

        target_email = "contactsapnaportals@gmail.com"
        uploaded_file = request.files.get('document')

        encoded_file = ""
        file_name = "No Document Attached"
        if uploaded_file and uploaded_file.filename != '':
            file_bytes = uploaded_file.read()
            encoded_file = base64.b64encode(file_bytes).decode('utf-8')
            file_name = uploaded_file.filename

        # डायनेमिक एक्स्ट्रा फील्ड्स का HTML जनरेटर (कितने भी नए फील्ड्स जोड़ें, यहाँ अपने आप ढल जाएंगे)
        extra_html = ""
        if extra_fields:
            extra_html += '<h3 style="color: #34495e; font-size: 15px; border-left: 4px solid #8e44ad; padding-left: 10px; margin-top: 20px; margin-bottom: 10px;">📋 अन्य विवरण (Additional Details)</h3><table style="width: 100%; font-size: 14px; color: #333333; border-collapse: collapse;">'
            for k, v in extra_fields.items():
                extra_html += f'<tr style="background: #fdfefe;"><td style="padding: 8px; width: 35%;"><strong>{k}:</strong></td><td style="padding: 8px;">{v}</td></tr>'
            extra_html += '</table>'

        # अत्यधिक प्रोफेशनल और क्लीन ईमेल डिज़ाइन (बिना किसी अंदरूनी लीक के)
        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px;">
            <div style="max-width: 680px; background: #ffffff; padding: 35px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin: 0 auto; border-top: 6px solid #2c3e50;">
                
                <!-- Header -->
                <div style="text-align: center; border-bottom: 2px solid #ecf0f1; padding-bottom: 20px; margin-bottom: 25px;">
                    <h2 style="color: #2c3e50; margin: 0; font-size: 24px; font-weight: 700;">🖨️ Apna Print Portal</h2>
                    <p style="color: #7f8c8d; margin: 5px 0 0 0; font-size: 13px;">Official Notification System</p>
                </div>

                <!-- Badge -->
                <div style="background: linear-gradient(135deg, #e8f8f5, #d1f2eb); padding: 12px; border-radius: 8px; font-size: 14px; color: #117a65; border: 1px solid #a3e4d7; text-align: center; margin-bottom: 20px;">
                    <strong>Tracking ID:</strong> <span style="color: #0e6251;">{identifier}</span> &nbsp;|&nbsp; <strong>Source Form:</strong> <span style="color: #0e6251;">{form_source}</span>
                </div>

                <!-- Section: User Details -->
                <h3 style="color: #34495e; font-size: 15px; border-left: 4px solid #3498db; padding-left: 10px; margin-top: 20px; margin-bottom: 10px;">👤 यूजर विवरण (User Details)</h3>
                <table style="width: 100%; font-size: 14px; color: #333333; border-collapse: collapse;">
                    <tr style="background: #fdfefe;"><td style="padding: 8px; width: 35%;"><strong>Username:</strong></td><td style="padding: 8px;">{username}</td></tr>
                    <tr><td style="padding: 8px;"><strong>Full Name:</strong></td><td style="padding: 8px;">{name}</td></tr>
                    <tr style="background: #fdfefe;"><td style="padding: 8px;"><strong>Mobile:</strong></td><td style="padding: 8px;">{mobile}</td></tr>
                    <tr><td style="padding: 8px;"><strong>Alt Mobile:</strong></td><td style="padding: 8px;">{secondary_mobile}</td></tr>
                    <tr style="background: #fdfefe;"><td style="padding: 8px;"><strong>Email ID:</strong></td><td style="padding: 8px;">{user_email}</td></tr>
                </table>

                <!-- Section: Request / Query Details -->
                <h3 style="color: #34495e; font-size: 15px; border-left: 4px solid #e67e22; padding-left: 10px; margin-top: 20px; margin-bottom: 10px;">📄 अनुरोध विवरण (Request Info)</h3>
                <table style="width: 100%; font-size: 14px; color: #333333; border-collapse: collapse;">
                    <tr style="background: #fdfefe;"><td style="padding: 8px; width: 35%;"><strong>Category/Service:</strong></td><td style="padding: 8px;"><span style="background: #e67e22; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{service_type}</span></td></tr>
                    <tr><td style="padding: 8px;"><strong>Message/Query:</strong></td><td style="padding: 8px; color: #2c3e50;">{query_text}</td></tr>
                    <tr style="background: #fdfefe;"><td style="padding: 8px;"><strong>Attached Document:</strong></td><td style="padding: 8px; color: #2980b9; font-weight: bold;">{file_name}</td></tr>
                </table>

                <!-- Dynamic Extra Fields -->
                {extra_html}

                <!-- Footer Note & Copyright -->
                <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #ecf0f1; text-align: center; font-size: 12px; color: #95a5a6;">
                    <p style="margin: 0 0 5px 0;">© 2026 Apna Print Portal. All Rights Reserved.</p>
                    <p style="margin: 0;">यह एक ऑटोमेटेड सिक्योर नोटिफिकेशन मेल है।</p>
                </div>
            </div>
        </body>
        </html>
        """

        api_url = "https://api.brevo.com/v3/smtp/email"
        api_key = os.environ.get("BREVO_API_KEY") 
        
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        # यहाँ सब्जेक्ट को बिल्कुल साफ, प्रोफेशनल और सामान्य रखा गया है
        payload = {
            "sender": {"email": "contactsapnaportals@gmail.com", "name": "Apna Print Portal"},
            "to": [{"email": target_email}],
            "subject": f"New Request from Apna Print Portal [{identifier}]",
            "htmlContent": html_content
        }

        if encoded_file:
            payload["attachment"] = [
                {
                    "content": encoded_file,
                    "name": file_name
                }
            ]

        # बैकग्राउंड थ्रेड प्रोसेस
        email_thread = threading.Thread(
            target=send_order_email_background,
            args=(payload, headers, identifier, name, service_type)
        )
        email_thread.start()

        return jsonify({
            "status": "success", 
            "message": f"सफलतापूर्वक सबमिट हो गया है! ट्रैकिंग आईडी: {identifier}",
            "order_id": identifier
        }), 200

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        return jsonify({"status": "error", "message": f"सर्वर एरर: {str(e)}"}), 500

@app.route('/health-check', methods=['GET'])
def health_check(): return jsonify({"status": "alive"}), 200

@app.route('/dashboard', methods=['GET'])
def dashboard_view():
    return render_template('dashboard.html', api_keys=api_keys_status, logs=server_logs, sites=registered_sites)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
