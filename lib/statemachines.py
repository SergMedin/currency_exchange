from transitions import Machine


class OrderCreation:
    states = [
        "start",
        "type",
        "currency_from",
        "currency_to",
        "amount",
        "type_price",  # Absolute or relative
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
        self.machine.add_transition(
            "set_currency_from", "currency_from", "currency_to"
        )  # Currently not used
        self.machine.add_transition(
            "set_currency_to", "currency_to", "amount"
        )  # Currently not used
        self.machine.add_transition("set_amount", "amount", "type_price")
        self.machine.add_transition("set_type_price", "type_price", "price")
        self.machine.add_transition("set_price", "price", "min_op_threshold")
        self.machine.add_transition(
            "set_min_op_threshold", "min_op_threshold", "lifetime"
        )
        self.machine.add_transition("set_lifetime", "lifetime", "confirm")
        self.machine.add_transition("confirm", "confirm", "start")  # ?

        self.machine.add_transition("set_type_rubamd", "type", "amount")

    def after_state_change(self):
        pass  # FIXME: change to logging
