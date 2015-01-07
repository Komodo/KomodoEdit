import common

def parse(colors):

    colors = common.parseColors(colors)

    colors["baseFore"]          = colors["B02"]
    colors["baseForeBlend1"]    = colors["B01"]
    colors["baseForeBlend2"]    = colors["B03"]

    colors["baseBack"]          = colors["B07"]
    colors["baseBackBlend1"]    = colors["B06"]
    colors["baseBackBlend2"]    = colors["B05"]
    colors["baseBackBlend3"]    = colors["B04"]

    colors["comment"]           = colors["B04"]
    colors["commentBlend"]      = colors["B05"]

    return common.parseScheme(colors)

