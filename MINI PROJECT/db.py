import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="ai_creative",
        user="postgres",
        password="$Arpit2008$",   # change if different
        port="5432"
    )
    return conn