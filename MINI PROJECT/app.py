from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import bcrypt
import re
from db import get_connection
import jwt
import random
import smtplib
import os 
from email.mime.text import MIMEText
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
app.secret_key = "super_secret_key_123"
EMAIL = "your_email@gmail.com"
APP_PASSWORD = "your_app_password"

def send_otp(email, otp):
    msg = MIMEText(f"Your OTP is: {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"] = EMAIL
    msg["To"] = email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()



def is_valid_email(email):
    import re

    # format check
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False

    # allowed domains
    allowed_domains = ["gmail.com", "outlook.com", "gla.ac.in"]
    domain = email.split("@")[-1].lower()

    return domain in allowed_domains

# ------------------------
# GROQ API
# ------------------------

GROQ_API_KEY = "your_api_key_here"

API_URL = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}


def call_ai(prompt):
    try:
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(API_URL, headers=headers, json=payload)
        result = response.json()

        if "choices" not in result:
            return "AI service error"

        return result["choices"][0]["message"]["content"]

    except:
        return "AI request failed"

def send_otp(email, otp):
    try:
        msg = MIMEText(f"Your OTP is: {otp}")
        msg["Subject"] = "OTP Verification"
        msg["From"] = "test@example.com"
        msg["To"] = email

        server = smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525)
        server.login("d0832ceb1daa14", "e43ed42260ff00")

        server.send_message(msg)
        server.quit()

        print("✅ OTP sent")

    except Exception as e:
        print("❌ Email error:", e)


# ------------------------
# ROUTES
# ------------------------
@app.route("/send-otp", methods=["POST"])
def send_otp_api():
    try:
        data = request.json
        email = data.get("email")

        otp = str(random.randint(100000, 999999))

        session["otp"] = otp
        session["otp_email"] = email

        send_otp(email, otp)

        return jsonify({"status": "success"})

    except Exception as e:
        print("❌ API error:", e)
        return jsonify({"status": "fail"})


@app.route("/index")
def index():
    if "user_id" not in session:
        return redirect("/")
    return render_template("index.html")


# ------------------------
# SIGNUP (FIXED 🔥)
# ------------------------

@app.route("/signup", methods=["POST"])
def signup():

    data = request.json

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    # 🔥 MUST BE INSIDE FUNCTION (INDENTED)
    if not is_valid_email(email):
        return jsonify({
            "status": "fail",
            "message": "Only Gmail / Outlook / College email allowed"
        })

    print("SIGNUP EMAIL:", email)

    conn = get_connection()
    cur = conn.cursor()

    # check existing user
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"status": "fail", "message": "User already exists"})

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cur.execute(
        "INSERT INTO users (name,email,phone,password) VALUES (%s,%s,%s,%s)",
        (name, email, phone, hashed_password)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "success"})


# ------------------------
# LOGIN (FIXED 🔥)
# ------------------------

@app.route("/login", methods=["POST"])
def login():

    data = request.json

    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cur = conn.cursor()

    # ✅ ONLY EMAIL CHECK
    cur.execute(
        "SELECT id,password FROM users WHERE email=%s",
        (email,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        return jsonify({
            "status": "fail",
            "message": "Account not found. Please signup first."
        })

    user_id = user[0]
    stored_password = user[1]

    # ❌ empty password case
    if not stored_password:
        return jsonify({
            "status": "fail",
            "message": "Invalid account"
        })

    # ❌ wrong password
    if not bcrypt.checkpw(password.encode(), stored_password.encode()):
        return jsonify({
            "status": "fail",
            "message": "Wrong password"
        })

    session["user_id"] = user_id
    return jsonify({"status": "success"})


# ------------------------
# GOOGLE LOGIN (UNCHANGED)
# ------------------------

@app.route("/google-login", methods=["POST"])
def google_login():

    data = request.json
    token = data.get("token")

    try:
        decoded = jwt.decode(token, options={"verify_signature": False})

        email = decoded.get("email")
        name = decoded.get("name", "Google User")

        if not email:
            return jsonify({"status": "fail"})

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user:
            user_id = user[0]
        else:
            cur.execute(
                "INSERT INTO users (name,email,phone,password) VALUES (%s,%s,%s,%s)",
                (name, email, "", "")
            )
            conn.commit()

            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            user_id = cur.fetchone()[0]

        session["user_id"] = user_id

        cur.close()
        conn.close()

        return jsonify({"status": "success"})

    except:
        return jsonify({"status": "fail"})
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.json

        entered_otp = str(data.get("otp")).strip()
        entered_email = str(data.get("email")).strip()

        stored_otp = str(session.get("otp")).strip()
        stored_email = str(session.get("otp_email")).strip()

        print("ENTERED OTP:", entered_otp)
        print("STORED OTP:", stored_otp)
        print("ENTERED EMAIL:", entered_email)
        print("STORED EMAIL:", stored_email)

        if entered_otp == stored_otp and entered_email == stored_email:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "fail", "message": "Wrong OTP"})

    except Exception as e:
        print("❌ Verify error:", e)
        return jsonify({"status": "fail"})

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/auth")
def auth():
    return render_template("login.html")

@app.route("/app")
def app_page():
    return render_template("index.html")

# ------------------------
# AI FEATURES
# ------------------------

@app.route("/generate", methods=["POST"])
def generate():
    text = request.json.get("text")
    result = call_ai(f"Rewrite this text clearly:\n{text}")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO history (user_id, action, input_text, output_text) VALUES (%s,%s,%s,%s)",
        (session["user_id"], "generate", text, result)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"result": result})


@app.route("/correct", methods=["POST"])
def correct():
    text = request.json.get("text")
    result = call_ai(f"Correct grammar:\n{text}")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO history (user_id, action, input_text, output_text) VALUES (%s,%s,%s,%s)",
        (session["user_id"], "correct", text, result)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"result": result})


@app.route("/enhance", methods=["POST"])
def enhance():
    text = request.json.get("text")
    result = call_ai(f"Improve this writing:\n{text}")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO history (user_id, action, input_text, output_text) VALUES (%s,%s,%s,%s)",
        (session["user_id"], "enhance", text, result)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"result": result})


@app.route("/topic", methods=["POST"])
def topic():
    data = request.json
    topic = data.get("topic")
    length = data.get("length")

    result = call_ai(f"Write a {length} description about {topic}")
    return jsonify({"result": result})


@app.route("/wordcount", methods=["POST"])
def wordcount():
    text = request.json.get("text", "")
    return jsonify({
        "words": len(text.split()),
        "characters": len(text)
    })


@app.route("/professional", methods=["POST"])
def professional():
    text = request.json.get("text")
    result = call_ai(f"Analyze professionalism:\n{text}")
    return jsonify({"result": result})


@app.route("/plagiarism", methods=["POST"])
def plagiarism():
    text = request.json.get("text")
    result = call_ai(f"Check originality:\n{text}")
    return jsonify({"result": result})


# ------------------------
# LOGOUT
# ------------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ------------------------
# RUN
# ------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))