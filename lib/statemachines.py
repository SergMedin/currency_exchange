from transitions import Machine


class OrderCreation:
    states = [
        "start",
        "type",
        "currency_from",
        "currency_to",
        "amount",
        "price",
        "min_op_threshold",
        "lifetime",
        "confirm",
    ]

    def __init__(self, user_id):
        self.user_id = user_id
        self.machine = Machine(
            model=self,
            states=OrderCreation.states,
            initial="start",
            after_state_change="after_state_change",
        )
        self.machine.add_transition("new_order", "start", "type")
        self.machine.add_transition("set_type", "type", "currency_from")
        self.machine.add_transition("set_currency_from", "currency_from", "currency_to")
        self.machine.add_transition("set_currency_to", "currency_to", "amount")
        self.machine.add_transition("set_amount", "amount", "price")
        self.machine.add_transition("set_price", "price", "min_op_threshold")
        self.machine.add_transition("set_min_op_threshold", "min_op_threshold", "lifetime")
        self.machine.add_transition("set_lifetime", "lifetime", "confirm")
        self.machine.add_transition("confirm", "confirm", "start")  # ?

    def after_state_change(self):
        print(f"State changed to {self.state}")  # FIXME: change to logging
