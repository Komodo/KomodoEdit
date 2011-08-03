class Alice:
    def __init__(self, a):
        'give me an A'
class Bob:
    def __init__(self, b):
        'give me a B'
class Carl(Alice, Bob):
    pass
class Dan(Bob, Carl):
    pass
class Earl(Carl):
    pass
