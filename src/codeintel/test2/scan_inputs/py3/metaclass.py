# check if metaclasses are ignored

class Meta0(Foo):
    pass

class Meta1(metaclass=Foo):
    pass

class Meta2(Foo, metaclass=Bar):
    pass

class Meta3(Foo, metaclass=Bar, argx=Baz):
    pass

class Meta4(Foo, Qoox, metaclass=Bar, argx=Baz):
    pass


