#!/usr/bin/env python

import boot_shop.app

if __name__ == "__main__":
    telegram = boot_shop.app.init()
    print("Wating for TG messages")
    telegram.run_forever()
