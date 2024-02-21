# currency_exchange

## Goals
Simplify and _partially_ automate the currency exchange process through message recommendations for trading.


## Tech
- [Python] - Python 3.12

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

## Running tests
```sh
pytest
```

## Running bot
```sh
python main.py
```  

## License
The information will be available in future