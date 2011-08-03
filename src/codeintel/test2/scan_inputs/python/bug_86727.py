def fun(value):
    return 0
fun = wrapper(fun)

def fan(value):
    return 0
fan = dapper(fan, 1, 2)
