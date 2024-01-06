Welcome to the exchange service!

*Disclaimer*: Use the bot for informational purposes only. All responsibility for conducting transactions remains with you. The bot may contain errors, so please verify the amount and the recipient of the funds before proceeding with any transaction!

The bot operates with only one currency pair: RUB/AMD.
If orders match, they will be automatically closed or their trading amount will be reduced, and users who placed them will receive notifications about the need to make an exchange.
If there is an overlap between the buying and selling prices, the exchange rate will be calculated using the formula: `(selling_price + buying_price) / 2`

*CREATING AN ORDER*
You can create orders to buy or sell. The lifespan of an order can be set when it is created, but it cannot exceed 48 hours. Below are examples of orders:

Selling 1500 RUB at a rate of 4.54 AMD per 1 RUB, with the minimum transaction amount being 100 RUB and the order's lifespan being 24 hours:
```
/add sell 1500 RUB * 4.54 AMD min_amt 100 lifetime_h 24
```
Buying 1500 RUB at a rate of 4.60 AMD per 1 RUB, with the minimum transaction amount being 1500 RUB and the order's lifespan being 48 hours:
```
/add buy 1500 RUB * 4.60 AMD min_amt 1500 lifetime_h 48
```

*LISTING YOUR ORDER AND REMOVING IT*
After creating an order, it will be displayed in the list of orders. You can view the list of orders with the `/list` command.
You can delete an order with the `/remove <order ID>` command.

*EXCHANGE STATISTICS*
Try using the `/stat` command to get exchange statistics. It can be helpful before creating a new order.