import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
    
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
    #if not os.environ.get("API_KEY"):
    #raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get current user portfolio
    rows = db.execute("SELECT * FROM portfolio WHERE id = :user_id", user_id=session["user_id"])
    # Get user details for his cash
    user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
    # Get current price of the stock

    total = 0
    for row in rows:
        stock = lookup(row["symbol"])
        db.execute("UPDATE portfolio SET price = :price WHERE symbol = :symbol", price=stock["price"], symbol=row["symbol"])
        total += float(row["share"])*float(row["price"])

    return render_template("index.html", rows=rows, cash=user[0]["cash"], total=total+user[0]["cash"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if not lookup(request.form.get("symbol")):
            return apology("invalid symbol", 400)

        if not request.form.get("shares"):
            return apology("missing shares", 400)

        # if user can't afford this much with his/her money
        rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        stock = lookup(request.form.get("symbol"))
        cost = stock["price"] * float(request.form.get("shares"))
        if cost > rows[0]["cash"]:
            return apology("can't afford", 400)

        """Buy shares of stock"""
        # Update user cash after purchasing shares
        db.execute("UPDATE users SET cash = :cost WHERE id = :user_id", cost=rows[0]["cash"]-cost, user_id=session["user_id"])
        
        # Update user shares portfolio
        rows = db.execute("SELECT * FROM portfolio WHERE id = :user_id and symbol = :symbol", user_id=session["user_id"], symbol=stock["symbol"])

        # If current share already present in portfolio table update it
        if len(rows):
            db.execute("UPDATE portfolio SET share = :share, price = :price WHERE id = :user_id AND symbol = :symbol", user_id=session["user_id"], symbol=stock["symbol"], share=float(rows[0]["share"])+float(request.form.get("shares")), price=stock["price"])
        # If current share not present in portfolio table insert it
        else:
            db.execute("INSERT INTO portfolio ('id', 'name', 'symbol', 'share', 'price') VALUES (:user_id, :name, :symbol, :share, :price)", user_id=session["user_id"], name=stock["name"], symbol=stock["symbol"], share=request.form.get("shares"), price=stock["price"])

        # Insert transaction summary into transaction table
        db.execute("INSERT INTO transactions ('id', 'name', 'symbol', 'share', 'price') VALUES (:user_id, :name, :symbol, :share, :price)", user_id=session["user_id"], name=stock["name"], symbol=stock["symbol"], share=request.form.get("shares"), price=stock["price"])
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    # Get info of current user transactions table
    rows = db.execute("SELECT * FROM transactions WHERE id = :user_id", user_id=session["user_id"])
    """Show history of transactions"""
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Given name doesn't match any symbol
        if not lookup(request.form.get("symbol")):
            return apology("invalid symbol", 400)
    
        """Get stock quote."""
        stock = lookup(request.form.get("symbol"))
        name = stock["name"]
        symbol = stock["symbol"]
        price = usd(stock["price"])
        # Show requested symbol information
        return render_template("quoted.html", name=name, symbol=symbol, price=price)


    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("missing password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords doesn't match", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Check if username already exist
        if len(rows) != 0:
            return apology("username already taken", 400)

        """Register user"""
        db.execute("INSERT INTO users ('username', 'hash') VALUES (:username, :hash)", username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))
        return redirect("/")


    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # Get portfolio of the user who logged in
    rows = db.execute("SELECT * FROM portfolio WHERE id = :user_id", user_id=session["user_id"])
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Render apology if user leave the suymbol field
        if not any(d["symbol"] == request.form.get("symbol") for d in rows):
            return apology("missing symbol", 400)

        # Get current user selected share info
        row = db.execute("SELECT * FROM portfolio WHERE id = :user_id AND symbol = :symbol", user_id=session["user_id"], symbol=request.form.get("symbol"))
        
        # Render apology if selected shares are invalid (negative, more or empty)
        if int(request.form.get("shares")) > row[0]["share"] or int(request.form.get("shares")) < 0 or not request.form.get("shares"):
            return apology("too many shares", 400)

        """Sell shares of stock"""
        # Calculate cost of sold shares
        stock=lookup(request.form.get("symbol"))
        cost = stock["price"]*float(request.form.get("shares"))

        # Get user details for current cash
        rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        
        # Update user cash after purchasing shares
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash=rows[0]["cash"]+cost, user_id=session["user_id"])

        # Get current share info from portfolio table
        share_info = db.execute("SELECT * FROM portfolio WHERE id = :user_id AND symbol=:symbol", user_id=session["user_id"], symbol=request.form.get("symbol"))

        # IF user sold all share delelte the entry of that symbol from portfolio
        if share_info[0]["share"] == int(request.form.get("shares")):
            db.execute("DELETE from portfolio WHERE id = :user_id AND symbol=:symbol", user_id=session["user_id"], symbol=request.form.get("symbol"))            
        
        # Update users portfolio after by subtracting solded shares from current
        else:
            db.execute("UPDATE portfolio SET share = :share WHERE id = :user_id AND symbol = :symbol", share=share_info[0]["share"]-int(request.form.get("shares")), user_id=session["user_id"], symbol=request.form.get("symbol"))

        # Insert transaction summary into transaction table
        db.execute("INSERT INTO transactions ('id', 'name', 'symbol', 'share', 'price') VALUES (:user_id, :name, :symbol, :share, :price)", user_id=session["user_id"], name=stock["name"], symbol=stock["symbol"], share=-int(request.form.get("shares")), price=cost)
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", rows=rows)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    app.run()