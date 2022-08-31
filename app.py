import market_app as ma
from flask import Flask, request, abort, session, redirect, jsonify

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'super_secret_key'


@app.route('/', methods=['GET'])
def index():
    session['logged_in'] = False
    return '''<h1>Paper Trading and Analysis App</h1>
    <p><a href=login><button class=grey style="height:50px;width:100px">Login</button></a></p>
    <p><a href=register><button class=grey style="height:50px;width:100px">Register</button></a></p>
    '''


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('Username')
        password = request.form.get('Password')
        name = request.form.get('Name')
        if len(username) < 3 or len(password) < 8:
            return '''
            <h1>Error</h1>
            <p>Username must be at least 3 characters.</p>
            <p>Password must be at least 8 characters.</p>
            <p><a href="../register"><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
        register = ma.User(username, password, name).register()
        if register:
            return '''
            <h1>Registered!</h1>
            <p><a href="../"><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
        else:
            return '''
            <h1>User already exists!</h1>
            <p><a href="../register"><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''

    return '''<h1>New User Registration</h1>
           <form method="POST">
               <div><label>Name: <input type="text" name="Name"></label></div>
               <div><label>Username: <input type="text" name="Username"></label></div>
               <div><label>Password: <input type="text" name="Password"></label></div>
               <input type="submit" value="Register" style="height:50px;width:100px">
           </form>
           <p><a href="../"><button class=grey style="height:50px;width:100px">Back</button></a></p>
           '''


@app.route("/api/register", methods=['POST'])
def api_register():
    if 'username' not in request.json and 'password' not in request.json:
        return abort(400)
    username = request.json['username']
    password = request.json['password']
    name = '' if 'name' not in request.json else request.json['name']
    if len(username) < 3 or len(password) < 8:
        return abort(400)
    register = ma.User(username, password, name).register()
    if register:
        return jsonify(True)
    else:
        return abort(400, "User already exists")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('Username')
        password = request.form.get('Password')
        session['username'] = username
        session['password'] = password
        curr_user = ma.ActiveUser(username, password)
        if curr_user.logged_in:
            session['logged_in'] = True
            return redirect('/user')
        else:
            return '''
            <h1>Invalid credentials!</h1>
            <p><a href="../login"><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''

    return '''<h1>User Login</h1>
           <form method="POST">
               <div><label>Username: <input type="text" name="Username"></label></div>
               <div><label>Password: <input type="password" name="Password"></label></div>
               <input type="submit" value="Login" style="height:50px;width:100px">
           </form>
           <p><a href="../"><button class=grey style="height:50px;width:100px">Back</button></a></p>
           '''


@app.route("/api/login", methods=['POST'])
def api_login():
    if 'username' not in request.json and 'password' not in request.json:
        return abort(400)
    username = request.json['username']
    password = request.json['password']
    session['username'] = username
    session['password'] = password
    curr_user = ma.ActiveUser(username, password)
    if curr_user.logged_in:
        session['logged_in'] = True
        return jsonify(True)
    else:
        return abort(400, "Invalid credentials")


@app.route("/user", methods=['GET', 'POST'])
def home():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    name = curr_user.name if curr_user.name != '' else curr_user.username
    if request.method == 'POST':
        try:
            money = float(request.form.get('money'))
        except:
            return '''<h1>Invalid entry!</h1>
            <p>Money value must follow standard US dollar formatting</p>
            <p><a href=../user ><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
        if 'add' in request.form:
            curr_user.add_money(money)
        else:
            curr_user.remove_money(money)
        return redirect('/user')

    return f'''<h1>Welcome, {name}</h1>
            <p>Current Balance: ${curr_user.balance:,.2f}</p>
            <p>Holdings Value: ${curr_user.holdings_value():,.2f}</p>
            <form method="POST">
               <label>Money: <input type="text" name="money"></label><input type="submit" value="Add" name="add">
               <input type="submit" value="Remove" name="remove">
           </form>
           <p><a href=user/edit><button class=grey style="height:50px;width:100px">Edit Account</button></a></p>
           <p><a href=user/stocks><button class=grey style="height:50px;width:100px">Buy/Sell Stocks</button></a></p>
           <p><a href=user/transactions><button class=grey style="height:50px;width:100px">View Transactions</button></a></p>
           <p><a href=user/portfolio><button class=grey style="height:50px;width:100px">View Holdings</button></a></p>
           <p><a href=user/analysis><button class=grey style="height:50px;width:100px">Generate Portfolio</button></a></p>
           <p><a href=user/logout><button class=grey style="height:50px;width:100px">Log Out</button></a></p>
    '''


@app.route("/api/user", methods=['GET', 'POST'])
def api_home():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'POST':
        if 'add money' not in request.json and 'remove money' not in request.json:
            return abort(400, "Fields left blank")
        if 'add money' in request.json:
            money = request.json['add money']
            curr_user.add_money(money)
        if 'remove money' in request.json:
            money = request.json['remove money']
            result = curr_user.remove_money(money)
            if not result:
                return abort(400, "Cannot remove more than current balance")
        return jsonify(True)

    data = {"user": session['username'], "current balance": curr_user.balance,
            "holdings value": curr_user.holdings_value()}
    return jsonify(data)


@app.route("/user/edit", methods=['GET', 'POST'])
def edit():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'POST':
        if 'name_ch' in request.form:
            name = request.form.get('name')
            curr_user.change_name(name)
            return redirect('/user')

        if 'user' in request.form:
            try:
                new_username = request.form.get('username')
            except:
                return '''<h1>Field left blank!</h1>
                <p><a href="../user/edit"><button class=grey style="height:50px;width:100px">Back</button></a></p>
                '''
            if len(new_username) < 3:
                return '''
                <h1>Error</h1>
                <p>Username must be at least 3 characters.</p>
                <p><a href="../user/edit"><button class=grey style="height:50px;width:100px">Back</button></a></p>
                '''
            result = curr_user.change_username(new_username)
            if result:
                return redirect('/')
            else:
                return '''
                <h1>User already exists!</h1>
                <p><a href="../user/edit"><button class=grey style="height:50px;width:100px">Back</button></a></p>
                '''

        if 'pass' in request.form:
            try:
                new_password = request.form.get('password')
            except:
                return '''<h1>Field left blank!</h1>
                <p><a href="../user/edit"><button class=grey style="height:50px;width:100px">Back</button></a></p>
                '''
            if len(new_password) < 8:
                return '''
                <h1>Error</h1>
                <p>Password must be at least 8 characters.</p>
                <p><a href="../user/edit"><button class=grey style="height:50px;width:100px">Back</button></a></p>
                '''
            curr_user.change_password(new_password)
            return redirect('/')

        if 'delete' in request.form:
            curr_user.delete_user()
            return redirect('/')

    return f'''<h1>Edit Account</h1>
            <form method="POST">
            <div><label>Name: <input type="text" name="name"></label>
            <input type="submit" value="Change Name" name="name_ch">
            </div>
            <div><label>Username: <input type="text" name="username"></label>
            <input type="submit" value="Change Username" name="user">
            </div>
            <div><label>Password: <input type="text" name="password"></label>
            <input type="submit" value="Change Password" name="pass">
            </div>
           <input type="submit" value="Delete Account" name="delete" style="height:50px;width:100px">
           </form>
           <p><a href=../user><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''


@app.route("/api/user/edit", methods=['PATCH', 'PUT', 'DELETE'])
def api_edit():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'PATCH' or request.method == 'PUT':
        if 'username' not in request.json and 'password' not in request.json and 'name' not in request.json:
            return abort(400, "Fields left blank")

        if 'username' in request.json:
            if len(request.json['username']) < 3:
                return abort(400)
            username = request.json['username']
            result = curr_user.change_username(username)
            if not result:
                return abort(400, "Username already exists")

        if 'password' in request.json:
            if len(request.json['password']) < 8:
                return abort(400)
            password = request.json['password']
            curr_user.change_password(password)

        if 'name' in request.json:
            name = request.json['name']
            curr_user.change_name(name)

        return redirect('/api/user/logout')

    elif request.method == 'DELETE':
        try:
            curr_user.delete_user()
            return jsonify(True)
        except:
            return abort(400)


@app.route("/user/portfolio", methods=['GET', 'POST'])
def portfolio():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'POST':
        curr_user.chart_portfolio()
        return '''<h1>Portfolio Value Over Time</h1>
        <img src="../static/images/image.png"/>
        <p><a href=../user/portfolio><button class=grey style="height:50px;width:100px">Back</button></a></p>
        '''
    holdings = curr_user.holdings_df()
    holdings = '<p>No holdings!</p>' if holdings.empty else holdings.to_html()
    name = curr_user.username if curr_user.name == '' else curr_user.name
    return f'''<h1>{name}'s Holdings</h1>
    {holdings}
    <p>Holdings Value: ${curr_user.holdings_value():,.2f}
    <form method="POST">
    <input type="submit" value="View Graph" style="height:50px;width:100px">
    </form>
    <p><a href=../user><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''


@app.route("/api/user/portfolio", methods=['GET'])
def api_portfolio():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    holdings = curr_user.holdings()
    return jsonify(holdings)

@app.route("/api/user/chart", methods=['GET'])
def api_chart():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    curr_user.chart_portfolio()
    data = {"image location": "/static/images/image.png"}
    return jsonify(data)


@app.route("/user/analysis", methods=['GET', 'POST'])
def analysis():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'POST':
        index_dict = {'sp500': ma.sp500, 'dow': ma.dow, 'nasdaq': ma.nasdaq}
        index = index_dict[request.form.get('market')]
        try:
            budget = float(request.form.get('budget'))
            num_results = int(request.form.get('results'))
        except:
            return '''<h1>Invalid entry!</h1>
            <p>Budget must follow standard US dollar formatting</p>
            <p><a href=../user/analysis ><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
        if budget > curr_user.balance:
            return '''<h1>Invalid entry!</h1>
            <p>Budget must be less than or equal to balance!</p>
            <p><a href=../user/analysis ><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
        aggressive = True if request.form.get('aggressive') else False
        df_result = curr_user.generate_portfolio(
            index, budget, num_results, aggressive)
        df_html = df_result.to_html()
        session['budget'] = budget
        session['df_result'] = df_result.to_dict()
        return f'''<h1>Results:</h1>
        {df_html}
        </br>
        <p><a href=invest ><button class=grey style="height:50px;width:100px">Invest</button></a></p>
        <p><a href=../user/analysis><button class=grey style="height:50px;width:100px">Back</button></a></p>
        '''
    return f'''<h1>Market Analysis and Portfolio Generation</h1>
           <form method="POST">
                <div><label>Invest from:
                <select name="market">
                <option value ="sp500">S&P 500 (Recommended)</option>
                <option value ="dow">DOW JONES</option>
                <option value ="nasdaq">NASDAQ</option>
                </select> 
                </label>
                </div>
               <div><label>Budget: <input type="text" name="budget"></label></div>
               <div><label>Length of list (Top num results): <input type="number" name="results"></label></div>
               <div><label>Aggressive strategy: <input type="checkbox" name="aggressive" checked="True" value="True"></label></div>
               <input type="submit" value="Analyze">
           </form>
           <p><a href=../user><button class=grey style="height:50px;width:100px">Back</button></a></p>
           '''


@app.route("/api/user/analysis", methods=['POST'])
def api_analysis():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if 'market' not in request.json or 'budget' not in request.json or 'results num' not in request.json:
        return abort(400, "Fields left blank")
    index_dict = {'sp500': ma.sp500, 'dow': ma.dow, 'nasdaq': ma.nasdaq}
    index = index_dict[request.json['market']]
    try:
        budget = float(request.json['budget'])
        num_results = int(request.json['results num'])
    except:
        return abort(400, "Budget must follow standard US dollar formatting. Results num must be a valid integer.")
    if num_results < 1:
        return abort(400, "Results num must be at least 1")
    if budget > curr_user.balance:
        return abort(400, "Budget must be less than or equal to user balance")
    aggressive = True if request.json['aggressive'] else False
    df_result = curr_user.generate_portfolio(
        index, budget, num_results, aggressive)
    df_json = df_result.to_json()
    session['budget'] = budget
    session['df_result'] = df_result.to_dict()
    return df_json
    


@app.route("/user/invest")
def invest():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if 'budget' not in session or 'df_result' not in session:
        return f'''<h1>Please generate an investment portfolio first</h1>
        <p><a href=../user/analysis><button class=grey style="height:50px;width:100px">Generate Portfolio</button></a></p>
        <p><a href=../user><button class=grey style="height:50px;width:100px">Back</button></a></p>
        '''
    curr_user = ma.ActiveUser(session['username'], session['password'])
    df = ma.pd.DataFrame.from_dict(session['df_result'])
    table = curr_user.invest_from_results(session['budget'], df)
    final_table = table.to_html()
    return f'''<h1>Invested!</h1>
    {final_table}
    <p><a href=../user><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''
@app.route("/api/user/invest")
def api_invest():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if 'budget' not in session or 'df_result' not in session:
        return abort(400, "Must perform market analysis first")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    df = ma.pd.DataFrame.from_dict(session['df_result'])
    table = curr_user.invest_from_results(session['budget'], df)
    final_table = table.to_json()
    return final_table


@app.route("/user/logout")
def logout():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    session['logged_in'] = False
    return redirect('/')


@app.route("/api/user/logout")
def api_logout():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    session['logged_in'] = False
    return jsonify(True)


@app.route("/user/transactions")
def transactions():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    df = curr_user.transaction_history()
    df = '<p>No transacations!</p>' if df.empty else df.to_html()
    return f'''<h1>Transaction History<h1>
    {df}
    <p><a href=../user><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''

@app.route("/api/user/transactions")
def api_transactions():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    df = curr_user.transaction_history()
    df = jsonify(None) if df.empty else df.to_json()
    return df


@app.route("/user/stocks", methods=['GET', 'POST'])
def stocks():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'POST':
        ticker = request.form.get('ticker').upper()
        stock = ma.Stock(ticker)
        session['ticker'] = ticker
        return f'''<h1>{ticker} Data</h1>
        <p>Price: ${stock.curr_price}</p>
        <p><a href=stocks/buy><button class=grey style="height:50px;width:100px">Buy</button></a></p>
        <p><a href=stocks/sell><button class=grey style="height:50px;width:100px">Sell</button></a></p>
        <p><a href=stocks/data><button class=grey style="height:50px;width:100px">Performance</button></a></p>
        <p><a href=../user/stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
        '''
    html_string = ''
    holdings_html = ''
    for name in ma.nasdaq:
        html_string += f'<option value ="{name}">{name}</option>'
    for name in curr_user.holdings():
        holdings_html += f'<option value ="{name}">{name}</option>'
    session['ticker'] = None
    return f'''<h1>Stock Data</h1>
    <form method="POST">
    <div><label>Select Ticker:
                <select name="ticker">
                {html_string}
                </select> 
                </label>
                </div>
    <input type="submit" value="Select">
    </form>
    <form method="POST">
    <div><label>Select From Holdings:
                <select name="ticker">
                {holdings_html}
                </select> 
                </label>
                </div>
    <input type="submit" value="Select">
    </form>
    <p><a href=../user><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''


@app.route("/api/stocks", methods=['POST'])
def api_stocks():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if 'ticker' not in request.json:
        return abort(400, "Must include ticker name")
    ticker = request.json['ticker']
    try:
        stock = ma.Stock(ticker)
    except:
        return abort(400, "Invalid ticker")
    data = {"ticker": ticker, "name": stock.name,
            "current price": stock.curr_price}
    return jsonify(data)


@app.route("/user/stocks/buy", methods=['GET', 'POST'])
def buy():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if not session['ticker']:
        return redirect('user/stocks')
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'POST':
        amount = int(request.form.get('amount'))
        stock = ma.Stock(session['ticker'])
        cost = stock.curr_price * amount
        if stock.buy(curr_user, amount):
            return f'''<h1>Bought {amount} shares of {session['ticker']} for ${cost:,.2f}</h1>
            <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
        else:
            return '''<h1>Transaction Failed!</h1>
            <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
    try:
        max_num = curr_user.holdings()[session['ticker']]
    except:
        max_num = 0
    return f'''<h1>Buy {session['ticker']}</h1>
    <p>Currently Holding {max_num} Shares</p>
    <form method="POST">
    <label>Enter Amount: <input type="number" name="amount"></label><input type="submit" value="Buy">
    </form>
    <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''


@app.route("/api/stocks/buy", methods=['POST'])
def api_buy():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if 'ticker' not in request.json or 'amount' not in request.json:
        return abort(400, "Must include valid ticker (str) and amount (int)")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    try:
        amount = int(request.json['amount'])
    except:
        return abort(400, "Amount must be valid integer")
    ticker = request.json['ticker']
    stock = ma.Stock(ticker)
    if stock.buy(curr_user, amount):
        return jsonify(True)
    else:
        return abort(400, "Transaction failed. Ensure user balance is greater than cost of transaction")


@app.route("/user/stocks/sell", methods=['GET', 'POST'])
def sell():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if not session['ticker']:
        return redirect('user/stocks')
    curr_user = ma.ActiveUser(session['username'], session['password'])
    if request.method == 'POST':
        amount = int(request.form.get('amount'))
        stock = ma.Stock(session['ticker'])
        cost = stock.curr_price * amount
        if stock.sell(curr_user, amount):
            return f'''<h1>Sold {amount} shares of {session['ticker']} for ${cost:,.2f}</h1>
            <p><a href=../stocks<button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
        else:
            return '''<h1>Transaction Failed!</h1>
            <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
            '''
    try:
        max_num = curr_user.holdings()[session['ticker']]
    except:
        return f'''<h1>No {session['ticker']} Currently Held!</h1>
        <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
        '''
    return f'''<h1>Sell {session['ticker']}</h1>
    <p>Currently Holding {max_num} Shares</p>
    <form method="POST">
    <label>Enter Amount: <input type="number" name="amount" min=1 max={max_num}></label><input type="submit" value="Sell">
    </form>
    <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''


@app.route("/api/stocks/sell", methods=['POST'])
def api_sell():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if 'ticker' not in request.json or 'amount' not in request.json:
        return abort(400, "Must include valid ticker (str) and amount (int)")
    curr_user = ma.ActiveUser(session['username'], session['password'])
    try:
        amount = int(request.json['amount'])
    except:
        return abort(400, "Amount must be valid integer")
    ticker = request.json['ticker']
    stock = ma.Stock(ticker)
    if stock.sell(curr_user, amount):
        return jsonify(True)
    else:
        return abort(400, f"Transaction failed. Ensure user is holding appropriate amount of {ticker} before attempting to sell")


@app.route("/user/stocks/data", methods=['GET', 'POST'])
def data():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if not session['ticker']:
        return redirect('user/stocks')
    if request.method == 'POST':
        stock = ma.Stock(session['ticker'])
        timeframe = request.form.get('timeframe')
        stock.chart_price(timeframe)
        return f'''<h1>{session['ticker']} Value Over Time</h1>
        <img src="../../static/images/image.png"/>
        <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
        '''
    return f'''<h1>Chart Performance of {session['ticker']}</h1>
    <form method="POST">
                <label>Select Timeframe:
                <select name="timeframe">
                <option value ="1y">1 Year</option>
                <option value ="ytd">YTD</option>
                <option value ="6mo">6 Months</option>
                <option value ="3mo">3 Months</option>
                <option value ="1mo">1 Month</option>
                </select> 
                </label>  
    <input type="submit" value="Chart">
    </form>
    <p><a href=../stocks><button class=grey style="height:50px;width:100px">Back</button></a></p>
    '''


@app.route("/api/stocks/data", methods=['POST'])
def api_data():
    if not session['logged_in']:
        return abort(401, description="Must be logged in to access")
    if 'ticker' not in request.json or 'timeframe' not in request.json:
        return abort(400, "Fields left blank")
    ticker = request.json['ticker']
    timeframe = request.json['timeframe']
    stock = ma.Stock(ticker)
    try:
        stock.chart_price(timeframe)
    except:
        return abort(400)
    data = {"image location": "/static/images/image.png"}
    return jsonify(data)
