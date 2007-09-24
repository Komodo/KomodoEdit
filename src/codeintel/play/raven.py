"""The Raven"""

__author__ = "Edgar Allen Poe"

from figures_of_speech import rhyme, alliteration
from poetry import Character

class Raven(Character):
    "black, creepy thing"
    quoth = "Nevermore!"
    def speak(self, dialog=None):
        if dialog is None:
            dialog = self.quoth
        print dialog

class Person(Character):
    def __init__(self, name):
        self.name = name
    def lament(self):
        print "sorrow for the lost %s" % self.name

def recite():
    "recite this poem"
    import hi, random
    raven = Raven()
    lenore = Person("lenore")
    for i in range(random.randint(1, 10)):
        rhyme()
        raven.speak()
        lenore.lament()
        alliteration()

if name == "__main__":
    recite()