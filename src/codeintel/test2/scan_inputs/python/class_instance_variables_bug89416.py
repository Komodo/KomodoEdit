class AClass(object):
    def __init__(self):
        self.one,self.two,self.three = gimme()
        self.four,self.five = (4,5)
        self.six = gimme()
        self.seven, self.eight = (gimme(), gimme())

    def gimme():
        return (1,2,3)
