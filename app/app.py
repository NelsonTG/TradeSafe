import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session 
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from decimal import Decimal
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

def getSnowflake():
    with open(os.environ["SNOWFLAKE_KEY_PATH"], "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user="NELSONT",
        private_key=key_bytes,
        role="ACCOUNTADMIN",
        warehouse="SP500",
        database="TICKERS",
        schema="PUBLIC",
    )

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

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return jsonify({"error": "not logged in"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route("/me")
@login_required
def me():
    user_id = current_user()
    conn = getConnection()
    cursor = conn.cursor()
    cursor.execute("""
    select username,email,cash from users where id = %s
    """, (user_id, ))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    username, email,cash = row
    return jsonify({
        "username":username,
        "email":email,
        "cash":float(cash),
    })

@app.route("/transactions/<name>")
@login_required
def transactions(name):
    user_id = current_user()
    conn = getConnection()
    cursor = conn.cursor()
    try:
        cursor.execute("select username from users where id = %s", (user_id,))
        me = cursor.fetchone()
        if me is None or me[0] != name:
            return jsonify({"error": "forbidden"}), 403
        cursor.execute(
            """select ticker, side, shares, price, executed_at from transactions where user_id = %s order by executed_at desc""",
            (user_id,),)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    history = []
    for ticker, side, shares, price, executed_at in rows:
        history.append({
            "ticker": ticker,
            "side": side,
            "shares": float(shares),
            "price": float(price),
            "executed_at": executed_at.isoformat(),
        })
    return jsonify(history)

@app.route("/company/<ticker>")
def company(ticker):
    conn = getSnowflake()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """select company_name, market_cap, city, state, price_date, close_price
            from COMPANY_LATEST_PRICE where ticker = %s""",
            (ticker.upper(),),)
        row = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    if row is None:
        return jsonify({"error": "unknown ticker"}), 404
    name, cap, city, state, price_date, price = row
    return jsonify({
        "ticker": ticker.upper(),
        "company_name": name,
        "market_cap": float(cap) if cap is not None else None,
        "city": city,
        "state": state,
        "price_date": str(price_date),
        "price": float(price) if price is not None else None,
    })


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


from decimal import Decimal

@app.route("/trade", methods=["POST"])
@login_required
def trade():
    user_id = current_user()
    ticker = request.form["ticker"].upper()
    side = request.form["side"]
    shares = Decimal(request.form["shares"])
    if side not in ("buy", "sell") or shares <= 0:
        return jsonify({"error": "bad request"}), 400
    conn = getConnection()
    cursor = conn.cursor()
    try:
        cursor.execute("""select price from latest_prices where ticker = %s""", (ticker,))
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "unknown ticker"}), 404
        price = row[0]
        cost = shares * price
        cursor.execute("""select cash from users where id = %s for update""", (user_id,))
        cash = cursor.fetchone()[0]
        if side == "buy":
            if cash < cost:
                return jsonify({"error": "insufficient cash"}), 400
            delta = -cost
        else:
            cursor.execute(
                """select coalesce(sum(case when side = 'buy' then shares else -shares end), 0) from transactions where user_id = %s and ticker = %s""",
                (user_id, ticker),)
            if cursor.fetchone()[0] < shares:
                return jsonify({"error": "not enough shares"}), 400
            delta = cost

        cursor.execute(
            """insert into transactions (user_id, ticker, side, shares, price) values (%s, %s, %s, %s, %s)",
            (user_id, ticker, side, shares, price),)
        cursor.execute(
            "update users set cash = cash + %s where id = %s",
            (delta, user_id),)
        conn.commit()
        return jsonify({"status": "ok", "price": float(price)}), 201
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

@app.route("/companies")
@login_required
def companies():
    conn = getSnowflake()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """select ticker, company_name, market_cap, close_price from COMPANY_LATEST_PRICE order by ticker
            """)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    result = []
    for ticker, name, cap, price in rows:
        result.append({
            "ticker": ticker,
            "company_name": name,
            "market_cap": float(cap) if cap is not None else None,
            "price": float(price) if price is not None else None,
        })
    return jsonify(result)

@app.route("/portfolio/<name>")
@login_required
def port(name):
    user_id = current_user()
    conn = getConnection()
    cursor = conn.cursor()
    try:
        cursor.execute("""select username from users where id = %s""", (user_id,))
        me = cursor.fetchone()
        if me is None or me[0] != name:
            return jsonify({"error": "forbidden"}), 403
        cursor.execute(
            """select ticker, shares from holdings where user_id = %s and shares > 0""",
            (user_id,),)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    positions = {}
    for ticker, shares in rows:
        positions[ticker] = float(shares)
    return jsonify(positions)

def get_list_id(cursor, user_id, list_name):
    cursor.execute(
        """select id from watchlists where user_id = %s and name = %s""",
        (user_id, list_name),)
    row = cursor.fetchone()
    return row[0] if row else None


@app.route("/watchlists", methods=["GET", "POST"])
@login_required
def watchlists():
    user_id = current_user()
    conn = getConnection()
    cursor = conn.cursor()
    try:
        if request.method == "GET":
            cursor.execute(
                """select name from watchlists where user_id = %s order by name""",(user_id,),)
            return jsonify([r[0] for r in cursor.fetchall()])
        name = request.form["name"].strip()
        cursor.execute(
            """insert into watchlists (user_id, name) values (%s, %s)
            on conflict do nothing""",
            (user_id, name),)
        conn.commit()
        return jsonify({"status": "created", "name": name}), 201
    finally:
        cursor.close()
        conn.close()


@app.route("/watchlists/<list_name>", methods=["GET", "POST"])
@login_required
def watchlist_items(list_name):
    user_id = current_user()
    conn = getConnection()
    cursor = conn.cursor()
    try:
        list_id = get_list_id(cursor, user_id, list_name)
        if list_id is None:
            return jsonify({"error": "no such list"}), 404
        if request.method == "GET":
            cursor.execute(
                """select ticker from watchlist_items where watchlist_id = %s order by ticker""",
                (list_id,),)
            return jsonify([r[0] for r in cursor.fetchall()])
        ticker = request.form["ticker"].upper()
        cursor.execute(
            """insert into watchlist_items (watchlist_id, ticker) values (%s, %s) on conflict do nothing""",
            (list_id, ticker),)
        conn.commit()
        return jsonify({"status": "added", "ticker": ticker}), 201
    finally:
        cursor.close()
        conn.close()

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

@app.route("/watchlists/<list_name>", methods=["DELETE"])
@login_required
def delete_watchlist(list_name):
    user_id = current_user()
    conn = getConnection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """delete from watchlists where user_id = %s and name = %s""",(user_id, list_name),)
        conn.commit()
        return jsonify({"status": "deleted", "name": list_name})
    finally:
        cursor.close()
        conn.close()

@app.route("/watchlists/<list_name>/<ticker>", methods=["DELETE"])
@login_required
def remove_ticker(list_name, ticker):
    user_id = current_user()
    conn = getConnection()
    cursor = conn.cursor()
    try:
        list_id = get_list_id(cursor, user_id, list_name)
        if list_id is None:
            return jsonify({"error": "no such list"}), 404
        cursor.execute(
            """delete from watchlist_items where watchlist_id = %s and ticker = %s""",
            (list_id, ticker.upper()),)
        conn.commit()
        return jsonify({"status": "removed", "ticker": ticker.upper()})
    finally:
        cursor.close()
        conn.close()

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"success":"logged out"})    