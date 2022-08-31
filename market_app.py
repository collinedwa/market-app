import yfinance as yf
import datetime as dt
import time
import pandas as pd
import numpy as np
from pandas_datareader import data as pdr
from statistics import mean
import psycopg2
import sqlalchemy
import matplotlib.pyplot as matplt
from scipy.stats import percentileofscore as pscore
from tqdm import tqdm
import bcrypt

yf.pdr_override()
sqla_string = 'postgresql+psycopg2://postgres:@localhost:5432/market_app_database'
psycopg2_string = 'postgres://postgres:@localhost:5432/market_app_database'
alchemy_engine = sqlalchemy.create_engine(sqla_string)
conn = psycopg2.connect(psycopg2_string)
conn.autocommit = True
sqla_conn = alchemy_engine.connect()
sp500 = pd.read_csv("tickers/sp500_tickers.csv", na_filter=False)['tickers'].tolist()
dow = pd.read_csv("tickers/dow_tickers.csv", na_filter=False)['tickers'].tolist()
nasdaq = pd.read_csv("tickers/nasdaq_tickers.csv", na_filter=False)['tickers'].tolist()


class User:
    '''
    Class which acts as the basis for user registration

    PARAMETERS

    username = desired username for registration, must be unique
    password = desired password for registration
    name = desired name for registration, optional
    '''

    def __init__(self, username: str, password: str, name=''):
        self.user_database = pd.read_sql(
            'SELECT * FROM user_accounts', sqla_conn)
        self.username = username
        self.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        self.name = name

    def register(self) -> bool:
        '''
        Adds account to user database, password is hashed before storing
        '''
        if self.username not in self.user_database['username'].unique():
            cursor = conn.cursor()
            SQL = f"""INSERT INTO user_accounts(username, password, name)
            VALUES ('{self.username}', '{self.password.decode()}', '{self.name}');"""
            cursor.execute(SQL)
            cursor.close()
            print('Registered!')
            return True
        else:
            print("User already exists!")
            return False


class ActiveUser:
    '''
    Class which allows for acount and market actions to be taken by a preexisting user

    PARAMETERS

    username = preexisting username in database
    password = prexisting username's corresponding password
    '''

    def __init__(self, username: str, password: str):
        self.logged_in = False
        self.user_database = pd.read_sql(
            'SELECT * FROM user_accounts', sqla_conn)
        if username in self.user_database['username'].unique() and bcrypt.checkpw(password.encode(),
         self.user_database.loc[self.user_database['username'] == username].values[0][2].encode()):
            print('Success')
            self.username = username
            self.password = password
            self.id = self.user_database.loc[self.user_database['username']
                                             == username].values[0][0]
            self.name = self.user_database.loc[self.user_database['username']
                                               == username].values[0][3]
            self.balance = self.user_database.loc[self.user_database['username']
                                                  == username].values[0][4]
            self.logged_in = True

    def change_username(self, username: str) -> bool:
        '''
        Changes the user's username if the provided string is unique within the database
        '''
        if username not in self.user_database['username'].unique():
            cursor = conn.cursor()
            SQL = f"""UPDATE user_accounts
            SET username = '{username}'
            WHERE id = {self.id};"""
            cursor.execute(SQL)
            cursor.close()
            print(f'Username changed to {username}')
            return True
        else:
            print('Username already in use!')
            return False

    def change_password(self, password: str) -> bool:
        '''
        Changes the user's password to the provided string
        '''
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cursor = conn.cursor()
        SQL = f"""UPDATE user_accounts
        SET password = '{hashed_pw.decode()}'
        WHERE id = {self.id};"""
        cursor.execute(SQL)
        cursor.close()
        print(f'Password changed to {password}')
        return True

    def change_name(self, name: str) -> bool:
        cursor = conn.cursor()
        SQL = f"""UPDATE user_accounts
        SET name = '{name}'
        WHERE id = {self.id};"""
        cursor.execute(SQL)
        cursor.close()
        print(f'Name changed to {name}')
        return True

    def add_money(self, amount: float):
        '''
        Adds the desired amount to a user's balance.
        Necessary for performing any market action
        '''
        self.balance += amount
        self.balance_adjustment()
        self.balance_snapshot()
        print(f"${amount:,.2f} added to balance. Total Balance: ${self.balance:,.2f}")
        return True
    
    def remove_money(self, amount: float):
        '''
        Removes the desired amount to a user's balance.
        '''
        if amount > self.balance:
            return False        
        self.balance -= amount
        self.balance_adjustment()
        self.balance_snapshot()
        print(f"${amount:,.2f} removed from balance. Total Balance: ${self.balance:,.2f}")
        return True

    def delete_user(self):
        '''
        Deletes the user account from the database
        '''
        cursor = conn.cursor()
        SQL = f"""DELETE FROM user_accounts
        WHERE id = {self.id};"""
        cursor.execute(SQL)
        cursor.close()

    def generate_portfolio(self, index: list, budget: float, num_shares: int, aggressive=True):
        '''
        Generates a recommended investment portfolio using Market functions
        '''
        if budget > self.balance:
            raise ValueError('Budget must be less than or equal to user balance')
        selected_index = Market(index)
        momentum_df = selected_index.momentum_investment_strategy(
            budget, num_shares, aggressive)
        combined_df = selected_index.value_investment_weighting(momentum_df)
        print('Results:')
        print(combined_df)
        return combined_df

    def invest_from_results(self, budget: float, combined_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Purchases from recommended stock dataframe
        '''
        name = []
        shares = []
        total_cost = []
        for ticker in combined_df.index:
            weight = combined_df.loc[ticker, 'combined weight']
            stock = Stock(ticker)
            amount = (budget*(weight))//stock.curr_price
            if amount == 0:
                continue
            stock.buy(self, amount)
            name.append(ticker)
            shares.append(amount)
            total_cost.append((stock.curr_price*amount))
        return pd.DataFrame(data={'Name':name,'Amount':shares,'Total Cost':total_cost})

    def balance_adjustment(self):
        '''
        Pushes adjusted balance value to database
        '''
        cursor = conn.cursor()
        SQL = f'''UPDATE user_accounts
        SET
            balance = {self.balance}
        WHERE
            username = '{self.username}';'''
        cursor.execute(SQL)
        cursor.close()
        return

    def balance_snapshot(self):
        '''
        Grabs snapshot of balance and logs it in balance_history table
        '''
        ts = dt.datetime.fromtimestamp(time.time())
        bal_date = ts.strftime('%Y,%m,%d')
        bal_time = ts.strftime('%H:%M:%S')
        cursor = conn.cursor()
        SQL = f"""INSERT INTO balance_history(balance_snapshot, holdings_value_snapshot, date, time, account_id)
        VALUES({self.balance}, {self.holdings_value()}, '{bal_date}', '{bal_time}', {self.id});"""
        cursor.execute(SQL)
        cursor.close()
        return

    def holdings(self):
        '''
        Returns dictionary of tickers and amounts from user's holdings
        '''
        holdings_db = pd.read_sql(
            f"SELECT * FROM holdings WHERE account_id = {self.id}", sqla_conn)
        if holdings_db.empty:
            holdings = None
        else:
            holdings = {}
            for ticker in holdings_db['ticker'].tolist():
                holdings_amount = holdings_db.loc[holdings_db['ticker']
                                                  == ticker].values[0][2]
                holdings[ticker] = holdings_amount
        return holdings

    def holdings_df(self):
        '''
        Returns a dataframe of tickers, amounts, and cost bases from user's holdings
        '''
        holdings_db = pd.read_sql(
            f"SELECT ticker, amount, cost_basis FROM holdings WHERE account_id = {self.id}", sqla_conn)
        return holdings_db


    def holdings_value(self):
        '''
        Calculates and returns current value of user's holdings
        '''
        holdings = self.holdings()
        if not holdings:
            return 0
        else:
            tickers = list(holdings.keys())
            holdings_value = 0
            closelist = pdr.get_data_yahoo(tickers,period='1d',interval='1m')
            closelist.dropna(inplace=True)
            if len(holdings) == 1:
                holdings_amount = holdings[tickers[0]]
                holdings_value += (closelist['Close'].iloc[-1]*holdings_amount)
            else:    
                for ticker in holdings:
                    holdings_amount = holdings[ticker]
                    holdings_value += (closelist['Close'].iloc[-1][ticker]*holdings_amount)
        return holdings_value

    def total_value(self):
        '''
        Returns user's sum of user's cash balance and holdings value
        '''
        holdings_value = self.holdings_value()
        return self.balance + holdings_value

    def value_history(self):
        self.balance_snapshot()
        balance_history_db = pd.read_sql(f'''SELECT balance_snapshot + holdings_value_snapshot AS total_value, 
        balance_snapshot, holdings_value_snapshot, date + time AS date_time
        FROM balance_history
        WHERE account_id = {self.id}''', sqla_conn)
        return balance_history_db
    
    def transaction_history(self):
        transaction_history_db = pd.read_sql(f'''SELECT ticker, price, bought, amount, date, time, total FROM market_transactions
        WHERE account_id = {self.id}''', sqla_conn)
        return transaction_history_db

    def chart_portfolio(self):
        '''
        Uses matplotlib to chart out the user's balance, holdings value, and combined value over time
        '''
        df = self.value_history()
        df.set_index('date_time', inplace=True)
        print(df)
        matplt.figure(figsize=(10, 10))
        matplt.plot(df['balance_snapshot'], 'g--', label='Cash Balance')
        matplt.plot(df['holdings_value_snapshot'],
                    'y--', label='Holdings Balance')
        matplt.plot(df['total_value'], label='Total Value')
        matplt.xlabel('Date/Time')
        matplt.ylabel('$ Value')
        matplt.title(f"{self.name}'s Portfolio Value")
        matplt.style.use("seaborn")
        matplt.legend()
        matplt.savefig('static/images/image.png')


class Stock:
    '''
    Class which acts as the basis for accessing stocks on the market

    PARAMETERS

    ticker: valid stock market ticker; will auto-capitalize
    '''

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.data = yf.Ticker(self.ticker).stats()
        self.name = self.data['price']['shortName']
        self.curr_price = self.data['price']['regularMarketPrice']

    def buy(self, user: ActiveUser, amount: int) -> bool:
        '''
        Pulls current market data for the stock and purchases the given amount, as long as the user has sufficient funds.
        Pushes data to the market_transactions and holdings tables afterward
        '''
        if amount <= 0:
            print('Amount must be greater than 0!')
            return False
        self.data = yf.Ticker(self.ticker).stats()
        self.curr_price = self.data['price']['regularMarketPrice']
        ts = dt.datetime.fromtimestamp(time.time())
        buy_date = ts.strftime('%Y,%m,%d')
        buy_time = ts.strftime('%H:%M:%S')
        total = self.curr_price*amount
        held_amount = pd.read_sql(
            f"SELECT amount FROM holdings WHERE ticker = '{self.ticker}' and account_id = {user.id}", sqla_conn)
        if held_amount.empty:
            held_amount = 0
        else:
            held_amount = held_amount.iloc[0][0]
        if user.balance >= total:
            print(
                f"Buying {amount} shares of {self.name} ({self.ticker}): ${total:,.2f}")
            user.balance -= total
            user.balance_adjustment()
            transaction_data = (self.ticker, self.curr_price, True, amount,
                                buy_date, buy_time, total, user.id)
            self.update_transactions(transaction_data)
            self.update_holdings(user, self.grab_cost_basis(
                user), (held_amount+amount))
            user.balance_snapshot()
            print('Transaction Complete!')
            return True
        else:
            print('Transaction Failed!')
            return False

    def sell(self, user: ActiveUser, amount: int) -> bool:
        '''
        Pulls current market data for the stock and sells the given amount, as long it is less than or equal to
        the amount within the user's holdings.
        Pushes data to the market_transactions and holdings tables afterward
        '''
        self.data = yf.Ticker(self.ticker).stats()
        self.curr_price = self.data['price']['regularMarketPrice']
        ts = dt.datetime.fromtimestamp(time.time())
        sell_date = ts.strftime('%Y,%m,%d')
        sell_time = ts.strftime('%H:%M:%S')
        total = self.curr_price*amount
        held_amount = pd.read_sql(
            f"SELECT amount FROM holdings WHERE ticker = '{self.ticker}' and account_id = {user.id}", sqla_conn)
        if held_amount.empty:
            held_amount = 0
        else:
            held_amount = held_amount.iloc[0][0]
        if held_amount >= amount:
            print(
                f"Selling {amount} shares of {self.name} ({self.ticker}): ${total:,.2f}")
            user.balance += total
            user.balance_adjustment()
            transaction_data = (self.ticker, self.curr_price, False, amount,
                                sell_date, sell_time, total, user.id)
            self.update_transactions(transaction_data)
            self.update_holdings(user, self.grab_cost_basis(
                user), (held_amount-amount))
            user.balance_snapshot()
            print('Transaction Complete!')
            return True
        else:
            print('Transaction Failed!')
            return False

    def update_transactions(self, data):
        '''
        Executes a SQL command to insert the transaction data into market_transactions
        '''
        cursor = conn.cursor()
        SQL = f"""INSERT INTO market_transactions(ticker, price, bought, amount, date, time, total, account_id)
        VALUES {data};"""
        cursor.execute(SQL)
        cursor.close()
        return

    def update_holdings(self, user, cost_basis, amount):
        '''
        Executes a SQL command to either insert or update the stock amount to the user's holdings
        '''
        cursor = conn.cursor()
        holdings_db = pd.read_sql(
            f"SELECT * FROM holdings WHERE ticker = '{self.ticker}' and account_id = {user.id}", sqla_conn)
        if holdings_db.empty:
            SQL = f"""INSERT INTO holdings(ticker, amount, cost_basis, account_id)
                    VALUES ('{self.ticker}', {amount}, {cost_basis}, {user.id});"""
        else:
            SQL = f"""UPDATE holdings SET cost_basis = {cost_basis}, amount = {amount}
            WHERE ticker = '{self.ticker}' and account_id = {user.id};
            DELETE FROM holdings WHERE amount = 0;"""
        cursor.execute(SQL)
        cursor.close()
        return

    def grab_cost_basis(self, user) -> float:
        '''
        Executes a SQL command to grab and return the cost basis (average buy-in price) of a stock
        based on the given user's transactions
        '''
        SQL = f"""SELECT AVG(price) FROM market_transactions
        WHERE account_id = {user.id} and ticker = '{self.ticker}' and bought = 'true';
        """
        cost_basis_df = pd.read_sql(SQL, sqla_conn)
        return cost_basis_df['avg'].iloc[0]

    def chart_price(self, timeframe='1y'):
        '''
        Uses matplotlib to chart out the stock's high, low, and closing prices from a given timeframe

        timeframe = '1Y', '9M', '6M', '3M', or '1M'
        '''
        accepted_values = ['1Y', '9M', '6M', '3M', '1M']
        if timeframe not in accepted_values:
            raise ValueError(
                f'Invalid timeframe! Expected one of {accepted_values}')
        df = pdr.get_data_yahoo(
            tickers=self.ticker, period='2y', interval='1d')
        matplt.figure(figsize=(10, 10))
        sma = df['Close'].rolling(21).mean().last(timeframe)
        lma = df['Close'].rolling(200).mean().last(timeframe)
        tf = df.last(timeframe)['Close']
        matplt.plot(sma, 'g--', label='21 Day Moving Average')
        matplt.plot(lma, 'y--', label='200 Day Moving Average')
        matplt.plot(tf, label='Closing Price')
        matplt.xlabel('Date/Time')
        matplt.ylabel('$ Value')
        matplt.title(f"{self.ticker} Price")
        matplt.style.use("seaborn")
        matplt.legend()
        matplt.savefig('static/images/image.png')


class Market:
    '''
    Class which contains all the functions necessary for pulling overall market data from a given index
    and performing analysis

    PARAMETERS

    index: list of tickers from a stock market index
    '''

    def __init__(self, index: list):
        self.index = index
        self.market_data = pdr.get_data_yahoo(
            tickers=self.index, period='1y', interval='1d')
        self.market_data.dropna(inplace=True)

    def momentum_investment_strategy(self, budget: float, num: int, aggressive=True) -> pd.DataFrame:
        '''
        Analyzes individual stock performances from the specified index and returns the top num performers
        from several time periods using a momentum-investing standpoint

        PARAMETERS

        num: number of stocks retrieved after analysis (top num results)
        aggressive: affects weight of volatility score; 
        set True for a more aggressive strategy or False for a more conservative one;
        '''
        momentum_stocks = {}
        '''
        Grabs the oldest and newest closing prices of a stock for 1y, 6 month, 3 month, and 1 month periods
        uses that data to calculate percentage gain and volatility
        Additionally rules out stocks which have a cost greater than 5% of the budget value (allows for lower budget investment options)
        '''
        for ticker in tqdm(self.index, desc='Gathering Momentum Investment Data'):
            if self.market_data['Close'].iloc[-1][ticker] > (budget*0.05):
                continue
            percent_gain_1y = (
                (self.market_data['Close'].iloc[-1][ticker]/self.market_data['Close'].iloc[0][ticker])-1)*100
            percent_gain_6m = (
                (self.market_data['Close'].iloc[-1][ticker]/self.market_data.last('6M')['Close'].iloc[0][ticker])-1)*100
            percent_gain_3m = (
                (self.market_data['Close'].iloc[-1][ticker]/self.market_data.last('3M')['Close'].iloc[0][ticker])-1)*100
            percent_gain_1m = (
                (self.market_data['Close'].iloc[-1][ticker]/self.market_data.last('1M')['Close'].iloc[0][ticker])-1)*100
            percent_gains = [percent_gain_1y/100, percent_gain_6m /
                             100, percent_gain_3m/100, percent_gain_1m/100]
            mean_return = mean(percent_gains)
            deviations = [np.std([percent, mean_return])
                          for percent in percent_gains]
            variance = sum([dev**2 for dev in deviations])/(len(deviations)-1)
            volatility = np.sqrt(variance)
            momentum_stocks[ticker] = {'1y return': percent_gain_1y, '1y percentile': 0, '6m return': percent_gain_6m, '6m percentile': 0,
                                       '3m return': percent_gain_3m, '3m percentile': 0, '1m return': percent_gain_1m, '1m percentile': 0,
                                       'final score': 0, 'volatility': volatility}
        momentum_df = pd.DataFrame(momentum_stocks).T
        time_periods = ['1y', '6m', '3m', '1m']
        '''
        Uses the scipy.stats.percentileofscore method to calculate the percentile of each return for each period
        '''
        for ticker in momentum_df.index:
            for period in time_periods:
                col = f'{period} return'
                percentile = f'{period} percentile'
                momentum_df.loc[ticker, percentile] = pscore(
                    momentum_df[col], momentum_df.loc[ticker, col])
        '''
        Calculates the mean of each percentile to give a final score to each stock
        '''
        for ticker in momentum_df.index:
            momentum_percentiles = [
                momentum_df.loc[ticker, f'{period} percentile'] for period in time_periods]
            momentum_df.loc[ticker, 'final score'] = mean(momentum_percentiles)

        momentum_df.sort_values('final score', ascending=False, inplace=True)
        momentum_df = momentum_df[:num] if num <= len(
            momentum_df.index) else momentum_df
        momentum_df['vol weight'] = 0
        volatility_sum = sum(momentum_df['volatility'].to_list())
        '''
        Assigns investing weights to stocks based on their volatility score and the 'aggressive' parameter
        '''
        if aggressive:
            for ticker in momentum_df.index:
                momentum_df.loc[ticker,
                                'vol weight'] = momentum_df.loc[ticker]['volatility']/volatility_sum
        else:
            volatility_weights = []
            for ticker in momentum_df.index:
                volatility_weights.append(
                    momentum_df.loc[ticker]['volatility']/volatility_sum)
            volatility_weights = sorted(volatility_weights)
            for ticker in momentum_df.sort_values('volatility', ascending=True).index:
                momentum_df.loc[ticker,
                                'vol weight'] = volatility_weights.pop()

        return momentum_df

    def value_investment_weighting(self, momentum_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Adds additional weighting to table of stocks with highest momentum based on projected value
        '''
        value_stocks = {}
        '''
        Gets key value metrics and stores them in a dictionary.
        Values that considered better when lower are stored as negatives to accurately calculate percentile scores
        Will set the value to NaN if no value can be obtained
        '''
        for ticker in tqdm(momentum_df.index, desc='Gathering Value Investment Data'):
            stock_data = Stock(ticker).data
            price_to_book = stock_data['defaultKeyStatistics']['priceToBook']
            price_to_book = -price_to_book if price_to_book else np.NaN
            forward_pe_ratio = stock_data['defaultKeyStatistics']['forwardPE']
            forward_pe_ratio = -forward_pe_ratio if forward_pe_ratio else np.NaN
            peg_ratio = stock_data['defaultKeyStatistics']['pegRatio']
            peg_ratio = -peg_ratio if peg_ratio else np.NaN
            free_cash_flow = stock_data['financialData']['freeCashflow']
            debt_to_equity = stock_data['financialData']['debtToEquity']
            debt_to_equity = -debt_to_equity if debt_to_equity else np.NaN
            value_stocks[ticker] = {'price to book': price_to_book, 'price to book percentile': 0, 'forward PE ratio': forward_pe_ratio,
                                    'forward PE ratio percentile': 0, 'PEG ratio': peg_ratio, 'PEG ratio percentile': 0,
                                    'free cash flow': free_cash_flow, 'free cash flow percentile': 0, 'debt to equity': debt_to_equity,
                                    'debt to equity percentile': 0, 'final score': 0, 'value weight': 0}
        value_df = pd.DataFrame(value_stocks).T
        '''
        Handles NaN cases by setting those values to the mean of all other values in the column
        '''
        for column in value_df.columns:
            value_df[column].fillna(value_df[column].mean(), inplace=True)

        value_prefixes = ['price to book', 'forward PE ratio',
                          'PEG ratio', 'free cash flow', 'debt to equity']
        '''
        Uses the scipy.stats.percentileofscore method to calculate the percentile of each metric
        '''
        for ticker in value_df.index:
            for prefix in value_prefixes:
                col = prefix
                percentile = f'{prefix} percentile'
                value_df.loc[ticker, percentile] = pscore(
                    value_df[col], value_df.loc[ticker, col])
        '''
        Calculates the mean of each percentile to give a final score to each stock
        '''
        for ticker in value_df.index:
            value_percentiles = [
                value_df.loc[ticker, f'{prefix} percentile'] for prefix in value_prefixes]
            value_df.loc[ticker, 'final score'] = mean(value_percentiles)

        score_sum = sum(value_df['final score'].to_list())

        for ticker in value_df.index:
            value_df.loc[ticker, 'value weight'] = (
                value_df.loc[ticker, 'final score']/score_sum)

        '''
        Calculates a final weighted score using the volatility weight and value weight metrics
        '''
        momentum_df['value weight'] = 0
        momentum_df['combined weight'] = 0
        for ticker in momentum_df.index:
            vol_weight = momentum_df.loc[ticker, 'vol weight']
            val_weight = value_df.loc[ticker, 'value weight']
            momentum_df.loc[ticker, 'value weight'] = val_weight
            momentum_df.loc[ticker, 'combined weight'] = (
                vol_weight + (val_weight*1.2))/2.2
        momentum_df.sort_values(
            'combined weight', ascending=False, inplace=True)

        return momentum_df