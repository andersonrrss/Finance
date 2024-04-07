import yfinance as yf

from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""
    
    # Transforma o símbolo em maiúsculas
    symbol = symbol.upper()
    
    try:
        # Obtenha os dados da ação usando yfinance
        stock = yf.Ticker(symbol)
        company_name = stock.info["longName"]
        
        # Obtenha o preço da ação
        price = stock.history(period="1d")["Close"].iloc[-1]
        
        return {"price": price, "symbol": symbol, "company_name": company_name}
    except Exception as e:
        return None



def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
