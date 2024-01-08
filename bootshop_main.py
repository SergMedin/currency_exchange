#!/usr/bin/env python

import bootshop.app

if __name__ == "__main__":
    telegram = bootshop.app.init()
    print("Wating for TG messages")
    telegram.run_forever()
