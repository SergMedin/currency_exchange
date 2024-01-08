#!/usr/bin/env python

import logging
import bootshop.app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    telegram = bootshop.app.init()
    print("Wating for TG messages")
    telegram.run_forever()
