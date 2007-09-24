# Test that CIX generation properly escapes some chars that are illegal
# in XML documents.

"""
     Name  Dec  Oct  Hex Literals
     ----------------------------
"""

def zero():
    "(nul)   0 0000 0x00 \x00 \0"
def one():
    "(soh)   1 0001 0x01 \x01 \1"
def two():
    "(stx)   2 0002 0x02 \x02 \2"
def three():
    "(etx)   3 0003 0x03 \x03 \3"
def four():
    "(eot)   4 0004 0x04 \x04 \4"
def five():
    "(enq)   5 0005 0x05 \x05 \5"
def six():
    "(ack)   6 0006 0x06 \x06 \6"
def seven():
    "(bel)   7 0007 0x07 \x07 \7 \a"
def eight():
    "(bs)    8 0010 0x08 \x08 \b"
def nine():
    "(ht)    9 0011 0x09 '\x09' '\t'"
def ten():
    "(nl)   10 0012 0x0a '\x0a' '\n'"
def eleven():
    "(vt)   11 0013 0x0b \x0b"
def twelve():
    "(np)   12 0014 0x0c \x0c \f"
def thirteen():
    "(cr)   13 0015 0x0d '\x0d' '\r'"
def fourteen():
    "(so)   14 0016 0x0e \x0e"
def fifteen():
    "(si)   15 0017 0x0f \x0f"
def sixteen():
    "(dle)  16 0020 0x10 \x10"
def seventeen():
    "(dc1)  17 0021 0x11 \x11"
def eighteen():
    "(dc2)  18 0022 0x12 \x12"
def nineteen():
    "(dc3)  19 0023 0x13 \x13"
def twenty():
    "(dc4)  20 0024 0x14 \x14"
def twenty_one():
    "(nak)  21 0025 0x15 \x15"
def twenty_two():
    "(syn)  22 0026 0x16 \x16"
def twenty_three():
    "(etb)  23 0027 0x17 \x17"
def twenty_four():
    "(can)  24 0030 0x18 \x18"
def twenty_five():
    "(em)   25 0031 0x19 \x19"
def twenty_six():
    "(sub)  26 0032 0x1a \x1a"
def twenty_seven():
    "(esc)  27 0033 0x1b \x1b"
def twenty_eight():
    "(fs)   28 0034 0x1c \x1c"
def twenty_nine():
    "(gs)   29 0035 0x1d \x1d"
def thirty():
    "(rs)   30 0036 0x1e \x1e"
def thirty_one():
    "(us)   31 0037 0x1f \x1f"

print __doc__
