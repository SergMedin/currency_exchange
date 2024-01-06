# currency_exchange
*Пока это черновик!*

## Цели
упростить и _частично_ автоматизировать процесс обмена валют для сотрудников Авито через сообщения-рекомендации для обмена.

## Минимальные функции
- принимать сообщения через бот о размещении заказ;
    - Из какой валюты в какую? **Пока только пара RUB-AMD**.
    - Сумма
    - Желаемый курс обмена (float с обменом)
    - Размер минимальной транзакции
    - Время существование заявки (24-48 часов по умолчанию)
- ✅ находить заявки подходящих пользователей;
- предоставлять информацию о статистике биржы через бота: минимальная цена продажи и максимальная цена покупки; количество заявок; курс последней сделки;
- возможность снимать и редактировать свои заявки через бот;
- ✅ когда срок заявки заканчивается, то она удаляется из списка активных заявок
- ✅ хранить данные в БД, чтобы подниматься из пепла;
- **уведомления**:
    - уведомлять пару пользователей и снимать эти заявки с биржи;
    - если заявка автоматически удаляется с биржи из-за истечения срока, то пользователю отправляется уведомление с возможностью пересоздать такую же заявку;

## Функции для светлого будущего
- черный список контактов (не хочу с ними меняться валютой)
- больше аналитики (потом расписать можно будет)
- более интерсных уведомлений: если вы понизите порог продажи, то вы сможете продать X рублей

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

## Running bot
```sh
python main.py
```  

## License

The information will be available in future