from __future__ import with_statement

def one():
    try:
        pass
    except:
        pass
    else:
        pass
    finally:
        pass

    try:
        pass
    except:
        pass
    else	:    # test with spacing and comments
        pass
    finally:
        pass

def two():
    try:
        pass
    except:
        pass
    finally:
        pass

    try:
        pass
    except:
        pass
    finally :
        pass

def three():
    try:
        pass
    except:
        pass

def four():
    try:
        pass
    finally:
        pass

def five():
    try:
        pass
    except:
        pass
    else:
        pass

# Uncomment this to get the test case to fail with a Python 2.4-based
# pythoncile.
#def six():
#    x = "yes" if True else "no"

def seven():
    # A Python 2.5-y script that uses both try/except/finally and with
    # statements.
    with open('/etc/passwd:', 'r') \
            as f:  # making this: hard 
        for line in f:
            print line

