*Operating Currency Pair*: The bot operates with only one currency pair: RUB/AMD.

*Order Matching*: If orders match, they will be automatically closed or their trading amount will be reduced. Users will receive notifications about the need to make an exchange. If there is an overlap between the buying and selling prices, the exchange rate will be the average of both.

*Exchange Statistics*
Use the /stat command to get insights on exchange activities, which can be helpful before creating a new order.

*Creating an Order*
You can create orders to buy or sell. The lifespan of an order can be set when it is created, but it cannot exceed 48 hours. Here are examples of orders:

_Selling_: 
```
/add sell 1500 RUB * 4.54 AMD min_amt 100 lifetime_h 24
```
where:
- 1500 is the amount in RUB;
- 4.54 is the rate in AMD per RUB;
- 100 is the minimum transaction amount in RUB;
- 24 is the order's lifetime in hours. After this time, the order will be automatically removed.

_Buying_:
```
/add buy 1500 RUB * 4.60 AMD min_amt 1500 lifetime_h 48
```
where:
- 1500 is the amount in RUB;
- 4.60 is the rate in AMD per RUB;
- 1500 is the minimum transaction amount in RUB;
- 48 is the order's lifetime in hours. After this time, the order will be automatically removed.

*Listing and Removing Orders*
- View your orders with the /list command.
- Remove an order with the `/remove <order ID>` command.