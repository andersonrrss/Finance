import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def create_tables():
    with sqlite3.connect("finance.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                username TEXT NOT NULL,
                hash TEXT NOT NULL,
                cash NUMERIC NOT NULL DEFAULT 10000.00
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buys (
                user_id INTEGER NOT NULL,
                symbol TEXT UNIQUE NOT NULL,
                shares NUMERIC NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return render_template("index.html")

@app.route("/stock")
def stock():
    # Inicia a conexão com o banco de dados
    conn = sqlite3.connect("finance.db")
    db = conn.cursor()

    # Armazena os valores que serão mostrados
    cash = db.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0]
    buys = []
    totalQuotes = 0
    total = 0

    quotes = db.execute("SELECT * FROM buys WHERE user_id = ?", (session["user_id"],)).fetchall()
    for quote in quotes:
        price = lookup(quote[1])["price"]
        name = lookup(quote[1])["company_name"]
        totalPrice = price * quote[2]
        # Armazena as informações de cada compania em forma de dicionário
        buys.append({
            "name": name,
            "symbol": quote[1],
            "price": usd(price),
            "shares": quote[2],
            "totalPrice": usd(totalPrice)
        })
        totalQuotes += quote[2]
        total += totalPrice

    # JSON que será retornado ao FRONTEND
    total += cash
    data = {
        "buys": buys,
        "totalQuotes": totalQuotes,
        "cash": usd(cash),
        "total": usd(total)
        
    }
    
    return jsonify(data)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        shares = request.form.get("shares")
        quote = lookup(request.form.get("symbol"))
        # Valida se o usuário inseriu as informações necessárias e válidas
        if not quote:
            return apology("Digite um simbolo válido")
        if not shares:
            return apology("Digite um número de ações a serem vendidas")
        # Transforma a quantidade de shares em um número inteiro
        try:
            shares = int(shares)
            if shares < 0:
                return apology("Digite um número válido")
        except:
            return apology("Insira uma quantidade válida")
        
        user_id = session["user_id"] 

        # Inicia a conexão com o banco de dados
        conn = sqlite3.connect("finance.db")
        db = conn.cursor()
        # Armazena a quantidade atual de dinheiro do usuário
        cash = db.execute("SELECT cash FROM users WHERE id = ?", (user_id,)).fetchone()[0]

        price = quote["price"] * shares
        # Checa se o usuário pode comprar as ações
        if cash < price:
            return apology("Dinheiro insuficiente")
        
        # Se o usuário nunca comprou essa ação o código cria uma nova linha na tabela
        if (db.execute("SELECT * FROM buys WHERE user_id = ? AND symbol = ?", (user_id, quote["symbol"])).fetchone()) is None:
            db.execute("INSERT INTO buys (user_id, symbol, shares) VALUES (?,?,?)", (user_id, quote["symbol"], shares))
        else:
            # Se o usuário já comprou essa ação antes então a quantidade de shares é mudada
            actShares = db.execute("SELECT shares FROM buys WHERE user_id = ? AND symbol = ?", (user_id, quote["symbol"])).fetchone()[0]
            newShares = actShares+shares
            # Atualiza a quantidade de shares da tabela
            db.execute("UPDATE buys SET shares = ? WHERE user_id = ? AND symbol = ?", (newShares, user_id, quote["symbol"]))
        
        # Atualiza o dinheiro do usuário
        newCash = cash-price
        db.execute("UPDATE users SET cash = ? WHERE id = ?", (newCash, user_id))

        conn.commit()
        conn.close()
        # Redireciona para a página principal
        return redirect("/")
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    conn = sqlite3.connect("finance.db")
    db = conn.cursor()
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        
        # Query database for username
        db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        rows = db.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Vê a qual empresa pertence esse símbolo
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        # Se o simbolo for válido
        if quote is not None:
            return render_template("quoted.html", quote=quote)
            
        return apology("Código inválido ou errado")

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    
    # Forget any user_id
    session.clear()

    #Armazena os valores digitados pelo usuário
    username = request.form.get("username")
    password = request.form.get("password")
    confirm = request.form.get("confirm")
    
    if request.method == "POST":
        # Valida se as informações foram colocadas pelo usuário
        if not username:
            return apology("Digite seu nome")
        
        if not password:
            return apology("Digite uma senha")
        
        if not confirm:
            return apology("Confirme sua senha")
        
        # Inicia a conexão com o banco de dados    
        conn = sqlite3.connect("finance.db")
        db = conn.cursor()
        checkname = db.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
        
        # Checa se o nome já está sendo usado
        if checkname is not None:
            return apology("Nome já registrado")
        
        # Checa se a senha foi devidamente confirmada
        if password.strip() != confirm.strip():
            return apology("Falha ao confirmar sua senha")

        # Gera o hash da senha
        hashPass = generate_password_hash(password)

        # Insere os dados do usuário no banco de dados
        db.execute("INSERT INTO users (username,hash) VALUES (?,?)", (username,hashPass))

        conn.commit()
        conn.close()
        return redirect("/login")
        
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")

        # Checa se o usuário forneceu as informações
        if not symbol:
            return apology("Insira um simbolo válido")
        
        if not shares:
            return apology("Insira a quantidade de ações a serem vendidas")

        # Converte a quantidade de ações a ser vendidas para int
        try:
            shares = int(shares)
            if shares < 1:
                return apology("Insira um número válido")
        except:
            return apology("Insira uma quantidade válida")
        
        user_id = session["user_id"]
        # Inicia a conexão com o banco de dados
        conn = sqlite3.connect("finance.db")
        db = conn.cursor()
        # Atualiza o número de ações do usuário
        actShares = db.execute("SELECT shares FROM buys WHERE user_id = ? AND symbol = ?", (user_id, symbol["symbol"])).fetchone()[0]
        
        print(actShares)

        newShares = actShares - shares
        print(newShares)
        # Checa se ele tem ações suficientes
        if newShares < 0:
            return apology("Você não tem esse número de ações")
        
        # Deleta a compania do perfil do usuário se ele vender todas as ações
        if newShares == 0:
            db.execute("DELETE FROM buys WHERE user_id = ? AND symbol = ?", (user_id, symbol["symbol"]))
        else:
            # Atualiza o número de ações se ainda sobrarem
            db.execute("UPDATE buys SET shares = ? WHERE user_id = ? AND symbol = ?", (newShares, user_id, symbol["symbol"]))

        # Atualiza o saldo do usuário
        actCash = db.execute("SELECT cash FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        newCash = actCash + (symbol["price"] * shares)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", (newCash, user_id))

        conn.commit()
        conn.close()
        return redirect("/")

    return render_template("sell.html")


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)