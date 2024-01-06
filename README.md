# currency_exchange

## Goals
Simplify and _partially_ automate the currency exchange process through message recommendations for trading.

## Features
- Support for RUB-AMD currency pair;
- Accept messages via a bot for order placement:
    - Amount
    - Desired exchange rate
    - Minimum transaction size
    - Order duration (up to 48 hours)
- Provide information about exchange statistics through the bot: minimum selling price and maximum buying price;
- Find matching orders from users and notify them;
- Ability to delete one's orders through the bot;
- When the order expires, it is removed from the list of active orders
- Data is stored in a database and can be recovered from the DB in case of a Python script failure.

## Tech
- [Python] - Python 3.11

## Docker-compose running:
Fill the .env file and then run command:
```sh
sudo docker compose -f docker-compose.local.yml
```
The volume with name 'currency_exchange_pg_data' will persistently contain application data

## Classic installation

Upgrade packet manager and install virtual environment (recommended):  
```sh
python -m pip install --upgrade pip
python -m venv venv

```  
Activation of virtual environment:  
Linux / MacOS:
```sh
source venv/bin/activate
```  
Windows (powershell):  
```sh
venv\Scripts\activate.ps1
```  
Install all dependecies:  
```sh
pip install -r requirements.txt
```  
  
Create .env file and fill it like in example (.env.example)

## Running test
```sh
./test
```

## Running bot
```sh
python main.py
```  

## License
The information will be available in future