import market_app as ma


def test_user():
    '''Registration'''
    new_user = ma.User('testuser', 'testpass', 'Test Name')
    assert new_user.register()
    assert new_user.password != 'testpass'
    conflict_user = ma.User('testuser', 'testpass', 'Test Name')
    assert conflict_user.register() == False


def test_active_user():
    '''ActiveUser functions'''
    active_user = ma.ActiveUser('testuser', 'testpass')
    assert active_user.logged_in
    fake_user = ma.ActiveUser('testwrong', 'testwrong')
    assert fake_user.logged_in == False

    assert active_user.change_name('Testing Name')
    assert active_user.change_password('passtest')
    active_user = ma.ActiveUser('testuser', 'passtest')
    assert active_user.change_username('test_user')
    active_user = ma.ActiveUser('test_user', 'passtest')
    assert active_user.add_money(1000)
    assert active_user.remove_money(100)
    assert active_user.remove_money(1000) == False
    holdings_test = active_user.holdings()
    assert holdings_test == None


def test_stock():
    '''Stock functions'''
    active_user = ma.ActiveUser('test_user', 'passtest')
    test_stock = ma.Stock('MSFT')
    assert test_stock.buy(active_user, 1)
    holdings_test = active_user.holdings()
    assert holdings_test == {'MSFT': 1}
    assert test_stock.sell(active_user, 1)
    assert test_stock.sell(active_user, 1) == False


def test_market():
    '''Market functions'''
    active_user = ma.ActiveUser('test_user', 'passtest')
    active_user.add_money(10000)
    portfolio = active_user.generate_portfolio(ma.sp500, 10000, 10)
    assert type(portfolio) == type(ma.pd.DataFrame())
    results = active_user.invest_from_results(10000, portfolio)
    assert type(results) == type(ma.pd.DataFrame())


def test_account_deletion():
    '''User deletion'''
    active_user = ma.ActiveUser('test_user', 'passtest')
    active_user.delete_user()
    user_check = ma.pd.read_sql(
        'SELECT * FROM user_accounts', ma.sqla_conn)
    assert 'testuser' not in user_check['username'].unique()
