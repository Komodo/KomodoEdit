
def foo():
    for p in sys.path:
        yield p

def bar():
    for n in range(10):
        yield n


