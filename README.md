# PTMA: Paper Trading and Market Analysis App

## Introduction:

This app is a combination paper trading/market analysis utility which scrapes data from Yahoo Finance to allow for pseudo-trading. It connects to a postgres database and logs user credentials, market transactions, balance changes, and holdings.

## Requirements:

* Docker
* See requirements.txt for Python-specific requirements

## Getting started:

* Ensure requirements are met, and that any preexisting postgres containers are disabled.
* Open a CLI and navigate to the project's root folder (with docker-compose.yml)
* Execute the command 'docker compose up -d'. This will start the container as well as initialize the database via [database_init.sql](initdb/database_init.sql)
* In the same directory, execute 'flask run'. This will startup the Flask web framework and host the application on http://127.0.0.1:5000/

## API Reference Table

| Path      | Methods | Parameters     | Description | 
| ---- | ---- | ---- | ---- |
| /api/register      | POST       | username: string, password: string, name: string   | User registration |
| /api/login   | POST       | username: string, password: string     | User login; must be registered |
| /api/user/logout | GET | | Logs user out |
| /api/user | GET | | Displays current user information |
| /api/user | POST | add money: float, remove money: float | Affects user's balance |
| /api/user/edit | PATCH, PUT | username: string, password: string, name: string | Changes user credentials |
| /api/user/edit | DELETE | | Deletes user account from database |
| /api/user/portfolio | GET | | Retrieves user portfolio information |
| /api/user/analysis | POST | market: str (sp500, dow, nasdaq), budget: float, results num: integer (at least 1), aggressive: bool (affects volatility weighting) | Analyzes given index and returns desired amount of top performing stocks |
| /api/user/invest | GET | | Invests from analysis results |
| /api/user/transactions | GET | | Returns list of market transactions made by user |
| /api/user/chart | GET | | Generates graph of user portfolio performance |
| /api/stocks | POST | ticker: string (Valid stock market ticker) | Retrieves current stock data | 
| /api/stocks/buy | POST | ticker: string, amount: integer | Purchases desired amount of stock |
| /api/stocks/sell | POST | ticker: string, amount: integer | Sells desired amount of stock if currently held |
| /api/stocks/data | POST | ticker: string, timeframe: string (1mo, 3mo, 6mo, ytd, 1y) | Generates graph of stock performance for given timeframe |


## Design and Implementation:


