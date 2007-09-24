
import os
import threading
import time
import random

def drive(fname):
    time.sleep(random.random())
    os.system("python ko.py "+fname) 

drivers = [threading.Thread(target=drive, args=(str(i),)) for i in range(10)]
for d in drivers: d.start()
for d in drivers: d.join()

