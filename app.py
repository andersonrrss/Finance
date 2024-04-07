import sqlite3
import datetime

from flask import Flask, redirect, render_template, request, session, jsonify
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

DATABASE = "finance.db"
def create_tables():
    with sqlite3.connect(DATABASE) as conn:
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
        # Em Action se for 0/false é compra e se for 1/true é venda
        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS history (
                user_id INTEGER FOREING KEY NOT NULL,
                symbol TEXT NOT NULL,
                action BOOLEAN,
                shares NUMERIC NOT NULL,
                date TIMESTAMP NOT NULL
            );
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
    conn = sqlite3.connect(DATABASE)
    db = conn.cursor()

    # Armazena os valores que serão mostrados
    cash = db.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0]

    user_id = session["user_id"]

    buys = []
    totalQuotes = 0
    total = 0

    symbols = db.execute("SELECT symbol FROM buys WHERE user_id = ?", (user_id,)).fetchall()
    for symbol in symbols:
        symbol = symbol[0]

        lookUp = lookup(symbol)
        price = lookUp["price"]
        name = lookUp["company_name"]

        shares = db.execute("SELECT shares FROM buys WHERE user_id = ? AND symbol = ?", (user_id, symbol)).fetchone()[0]
        totalPrice = price * shares
        # Armazena as informações de cada compania em forma de dicionário
        buys.append({
            "name": name,
            "symbol": symbol,
            "price": usd(price),
            "shares": shares,
            "totalPrice": usd(totalPrice)
        })
        totalQuotes += shares
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
        conn = sqlite3.connect(DATABASE)
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

        # Atualiza o histórico do usuário
        db.execute("INSERT INTO history (user_id, symbol,action,shares,date) VALUES (?,?,?,?,?)", (user_id, quote["symbol"], 0, shares, datetime.datetime.now()))

        conn.commit()
        conn.close()
        # Redireciona para a página principal
        return redirect("/")
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return render_template("history.html")

@app.route("/getHistory")
@login_required
def getHistory():
    
    
    with sqlite3.connect(DATABASE) as conn:
        user_id = session["user_id"]
        
        db = conn.cursor()
        history = db.execute("SELECT * FROM history WHERE user_id = ?", (user_id,)).fetchall()

        data = []
        
        if history:
            for row in history:
                price = lookup(row[1])["price"]
                action = row[2]
                if action:
                    action = "Venda"
                else:
                    action = "Compra"
                infos = {
                    "action": action,
                    "symbol": row[1],
                    "price": usd(price*row[3]),
                    "shares": row[3],
                    "date": row[4]
                }
                data.append(infos)

    return jsonify(data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    conn = sqlite3.connect(DATABASE)
    db = conn.cursor()
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")
        if not username:
            return apology("Digite um nome", 403)
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Digite uma senha", 403)
        username = username.strip().capitalize()

        
        # Query database for username
        db.execute("SELECT * FROM users WHERE username LIKE ?", (username,))
        rows = db.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("nome ou senha invalido(s)", 403)

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
        username = username.strip().capitalize()
        
        if not password:
            return apology("Digite uma senha")
        
        if not confirm:
            return apology("Confirme sua senha")
        
        # Inicia a conexão com o banco de dados    
        conn = sqlite3.connect(DATABASE)
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
    user_id = session["user_id"]

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
       

        # Checa se o usuário forneceu as informações
        if not symbol:
            return apology("Insira um simbolo")
        
        if not shares:
            return apology("Insira a quantidade de ações a serem vendidas")

        # Converte a quantidade de ações a ser vendidas para int
        try:
            shares = int(shares)
            if shares < 1:
                return apology("Insira um número válido")
        except:
            return apology("Insira uma quantidade válida")
        # Checa se o simbolo é um símbolo válido
        quote = lookup(symbol)
        if not quote:
            return apology("Insira um simbolo válido")

        # Inicia a conexão com o banco de dados
        conn = sqlite3.connect(DATABASE)
        db = conn.cursor()
       
        actShares = db.execute("SELECT shares FROM buys WHERE user_id = ? AND symbol = ?", (user_id, quote["symbol"])).fetchone()[0]
        #Checa se o usuário contém a ação
        if actShares is None:
            return apology("Você não tem essa ação")
        
        # Atualiza o número de ações do usuário
        newShares = actShares - shares

        # Checa se ele tem ações suficientes
        if newShares < 0:
            return apology("Você não tem esse número de ações")
        
        # Deleta a compania do perfil do usuário se ele vender todas as ações
        if newShares == 0:
            db.execute("DELETE FROM buys WHERE user_id = ? AND symbol = ?", (user_id, quote["symbol"]))
        else:
            # Atualiza o número de ações se ainda sobrarem
            db.execute("UPDATE buys SET shares = ? WHERE user_id = ? AND symbol = ?", (newShares, user_id, quote["symbol"]))


        # Atualiza o saldo do usuário
        actCash = db.execute("SELECT cash FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        newCash = actCash + (quote["price"] * shares)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", (newCash, user_id))

        # Atualiza o histórico do usuário
        db.execute("INSERT INTO history (user_id, symbol,action,shares,date) VALUES (?,?,?,?,?)", (user_id, quote["symbol"], 1, shares, datetime.datetime.now()))
        
        conn.commit()
        conn.close()
        return redirect("/")
    
    with sqlite3.connect(DATABASE) as conn:
        db = conn.cursor()
        symbols = db.execute("SELECT symbol FROM buys WHERE user_id = ?", (user_id,)).fetchall()
        if not symbols:
            mensagem = "Compre ações primeiro"
        else:
            mensagem = "Escolha uma ação para ser vendida"

    return render_template("sell.html", mensagem=mensagem ,symbols=symbols)


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)