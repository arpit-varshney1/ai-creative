from db import get_connection
import bcrypt

def create_user(name, email, phone, password):
    conn = get_connection()
    cur = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cur.execute(
        "INSERT INTO users (name,email,phone,password) VALUES (%s,%s,%s,%s)",
        (name, email, phone, hashed)
    )

    conn.commit()
    cur.close()
    conn.close()


def get_user(email, phone):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password FROM users WHERE email=%s AND phone=%s",
        (email, phone)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user