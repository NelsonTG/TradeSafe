import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session 
from werkzeug.security import generate_password_hash, check_password_hash
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
def getConnection():
    return psycopg2.connect(
        host="localhost",
        dbname="TradeSafe",
        user="tradesafe_app",
        password=os.environ["DB_PASSWORD"],
        port = 5432
    )

def current_user():
    return session.get("user_id")

@app.route("/transactions/<name>")
def transactions(name):
    user_id = current_user()
    if user_id is None:
        return jsonify({"error": "not logged in"}), 401
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("select username from users where id = %s", (user_id,))
    if cursor.fetchone()[0] != name:
        cursor.close()
        conn.close()
        return jsonify({"error": "forbidden"}), 403
    cursor.execute("""
    SELECT t.ticker,t.side,t.shares,t.price,t.executed_at from transactions t inner join users u on t.user_id = u.id where u.username = %s order by t.executed_at DESC
    """, (name,))
    row = cursor.fetchall()
    cursor.close()
    conn.close()
    history = []
    for ticker,side,shares,price, executed_at in row:
        history.append({
            "ticker": ticker,
            "side": side,
            "shares": float(shares),
            "price": float(price),
            "executed_at": executed_at.isoformat()
        })
    return jsonify(history)

@app.route("/company/<ticker>")
def company(ticker):
    return f"works"


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, password_hash from users where username = %s
    """, (username,),)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is None or not check_password_hash(row[1],password):
        return jsonify({"error":"invalid username or password"}),401
    session["user_id"] = row[0]
    return jsonify({"success":"logged in as","username":username})


@app.route("/trade")
def trade():
    if user_id is None:
        return jsonify({"error": "not logged in"}), 401
    ticker = request.form["ticker"]
    side = request.form["side"]
    shares = request.form["shares"]
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("""
    select * 
    """)
    if side == "buy":
        df
    elif side == "sell":
        df
    cursor.execute("""
    INSERT INTO TRANSACTIONS(id,user_id,ticker,side,shares,price,executed_at) VALUES
    (%s,%s,%s,%s,%s,%s,%s)
    """, ())


@app.route("/companies")
def companies():
    return f"companies"

@app.route("/portfolio/<name>")
def port(name):
    user_id = current_user()
    if user_id is None:
        return jsonify({"error": "not logged in"}), 401
    conn = getConnection()
    cursor = conn.cursor() 
    cursor.execute("select username from users where id = %s", (user_id,))
    me = cursor.fetchone()
    if me is None or me[0] != name:
        cursor.close()
        conn.close()
        return jsonify({"error": "forbidden"}), 403
    cursor.execute("""
    select ticker, shares from holdings where user_id = (select id from users where username = %s)and shares > 0;
    """,(name,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    port = {}
    for ticker,shares in rows:
        port[ticker] = float(shares)
    return jsonify(port)

@app.route("/watchlist/<name>", methods = ["GET","POST","DELETE"])
def watchlist(name):
    user_id = current_user()
    if user_id is None:
        return jsonify({"error": "not logged in"}), 401
    if request.method == "GET":
        conn = getConnection()
        cursor = conn.cursor() 
        cursor.execute("""
        SELECT 
        """)
    elif request.method == "POST":
        ticker = request.form["ticker"]
        
        conn = getConnection()
        cursor = conn.cursor() 
        cursor.execute("""
        create table watchlist (
        user_id  integer not null references users(id),
        ticker   text not null,
        primary key (user_id, ticker)
        );""")
        cursor.execute("""
        INSERT INTO watchlist(user_id,ticker)VALUES (%s,%s)
        """,(name,ticker))
        cursor.close()
        conn.close()
        return jsonify({"success":"watchlist created"})
    elif request.method == "DELETE":

@app.route("/create", methods= ["POST"])
def create():
    name = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("""
    select username, email from users where username = %s or email = %s
    """, (name,email))
    exists = cursor.fetchall()
    if exists:
        cursor.close()
        conn.close()
        return jsonify({"error": "username or email already in use"}), 409
    hashed = generate_password_hash(password)
    cursor.execute("""
    insert into users(username,email,password_hash) values (%s,%s,%s)
    """, (name,email,hashed))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status":"created"}),201

@app.route("/logout", methods=["POST"])
def logout():
    user_id = current_user()
    if user_id is None:
        return jsonify({"error": "not logged in"}), 401
    session.clear()
    return jsonify({"success":"logged out"})    