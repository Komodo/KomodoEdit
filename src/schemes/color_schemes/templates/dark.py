import common

def parse(colors):

    colors = common.parseColors(colors)

    colors["baseFore"]          = colors["B05"]
    colors["baseForeBlend1"]    = colors["B06"]
    colors["baseForeBlend2"]    = colors["B04"]

    colors["baseBack"]          = colors["B00"]
    colors["baseBackBlend1"]    = colors["B01"]
    colors["baseBackBlend2"]    = colors["B02"]
    colors["baseBackBlend3"]    = colors["B03"]

    colors["comment"]           = colors["B03"]
    colors["commentBlend"]      = colors["B04"]

    return common.parseScheme(colors)

