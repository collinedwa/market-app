SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'market_app_database' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS market_app_database;
CREATE DATABASE market_app_database;

\c market_app_database

CREATE TABLE user_accounts(
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT,
    balance DECIMAL(19,4) NOT NULL DEFAULT 0
);

CREATE TABLE market_transactions(
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    price DECIMAL(19,4) NOT NULL,
    bought BOOLEAN NOT NULL,
    amount INTEGER NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    total DECIMAL(19,4) NOT NULL,
    account_id INTEGER,
    CONSTRAINT fk_market_transactions_user
        FOREIGN KEY (account_id)
        REFERENCES user_accounts (id)
        ON DELETE SET NULL
);

CREATE TABLE holdings(
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    amount INTEGER NOT NULL,
    cost_basis DECIMAL(19,4) NOT NULL,
    account_id INTEGER,
    CONSTRAINT fk_holdings_user
        FOREIGN KEY (account_id)
        REFERENCES user_accounts (id)
        ON DELETE SET NULL
);

CREATE TABLE balance_history(
    id SERIAL PRIMARY KEY,
    balance_snapshot DECIMAL(19,4) NOT NULL,
    holdings_value_snapshot DECIMAL(19,4) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    account_id INTEGER,
    CONSTRAINT fk_balance_history_user
        FOREIGN KEY (account_id)
        REFERENCES user_accounts (id)
        ON DELETE SET NULL
);

CREATE INDEX user_transactions_index ON market_transactions USING HASH (account_id);

CREATE INDEX user_balance_index ON balance_history USING HASH (account_id);

CREATE INDEX user_holdings_index ON holdings USING HASH (account_id);

