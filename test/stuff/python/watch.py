a = 0

def recurse(b):
    if b > 10:
        print "a is ", a
        return
    recurse(b + 1)
    
recurse(a)

print "done"
