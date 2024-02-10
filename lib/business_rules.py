from decimal import Decimal, InvalidOperation
from .config import ORDER_LIFETIME_LIMIT


# FIXME: refactor it
class Validator:
    def validate_add_command_params(self, params):
        if len(params) != 10:
            raise ValueError("Invalid number of arguments")

        self.validate_order_type(params[0])
        self.validate_amount(params[1])
        self.validate_currency_from(params[2])
        if params[3] != "*":
            raise ValueError(f"Invalid separator: {params[3]}")
        self.validate_price(params[4])
        self.validate_currency_to(params[5])
        if params[6] != "min_amt":
            raise ValueError(f"Invalid separator: {params[6]}")
        self.validate_min_op_threshold(params[7], params[1])
        if params[8] != "lifetime_h":
            raise ValueError(f"Invalid separator: {params[8]}")
        self.validate_lifetime(params[9])

    def validate_order_type(self, order_type: str):
        if order_type.capitalize() not in ["Buy", "Sell"]:
            raise ValueError(f"Invalid order type: {order_type}")

    def validate_amount(self, amount: str):
        if not amount.isnumeric():
            raise ValueError(f"Invalid amount: {amount}")
        try:
            if Decimal(amount) <= 0:
                raise ValueError("Amount cannot be negative or zero")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {amount}")

    def validate_currency_from(self, currency_from: str):
        if currency_from.lower() not in ["rub"]:
            raise ValueError(f"Invalid currency: {currency_from}")

    def validate_currency_to(self, currency_to: str):
        if currency_to.lower() not in ["amd"]:
            raise ValueError(f"Invalid currency: {currency_to}")

    def validate_price(self, price: str | Decimal):
        try:
            price = Decimal(price)
            if price != price.quantize(Decimal("0.0001")):
                raise ValueError(
                    f"Price has more than four digits after the decimal point: {price}"
                )
            elif price <= 0:
                raise ValueError("Price cannot be negative or zero")
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {price}")

    def validate_min_op_threshold(
        self, min_op_threshold: str | Decimal, amount: str | Decimal
    ):
        try:
            min_op_threshold = Decimal(min_op_threshold)
            amount = Decimal(amount)
            if min_op_threshold < 0:
                raise ValueError("Minimum operational threshold cannot be negative")
            if min_op_threshold > amount:
                raise ValueError(
                    "Minimum operational threshold cannot be greater than the amount"
                )
        except InvalidOperation:
            raise ValueError(f"Invalid value for Decimal: {min_op_threshold}")

    def validate_lifetime(self, lifetime: str, limit_sec=ORDER_LIFETIME_LIMIT):
        if not lifetime.isnumeric():
            raise ValueError(f"Invalid lifetime: {lifetime}")
        if int(lifetime) < 0:
            raise ValueError("Lifetime cannot be negative")
        if int(lifetime) > (limit_sec // 3600):
            raise ValueError(
                f"Lifetime cannot be greater than {limit_sec // 3600} hours"
            )

    def validate_remove_command_params(self, params, exchange, user_id):
        if len(params) == 1:
            remove_order_id = params[0]
        else:
            raise ValueError(f"Invalid remove params: {params}")
        if not remove_order_id.isnumeric():
            raise ValueError(f"Invalid order id: {remove_order_id}")
        if int(remove_order_id) not in exchange._orders:
            raise ValueError(f"Invalid order id: {remove_order_id}")
        if exchange._orders[int(remove_order_id)].user.id != user_id:
            # User should not be able realize that order with this id exists
            raise ValueError(f"Invalid order id: {remove_order_id}")
