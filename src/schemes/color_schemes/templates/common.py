def hexToBGR(val):
    if type(val) == int:
        return val

    val = val.lstrip('#')
    if len(val) == 3:
        val += val

    r,g,b = int(val[:2], 16), int(val[2:4], 16), int(val[4:], 16)
    color = r+g*256+b*256*256
    return color

def parseColors(colors):

    colors = colors.copy()

    colors["B00"] = hexToBGR(colors["B00"])
    colors["B01"] = hexToBGR(colors["B01"])
    colors["B02"] = hexToBGR(colors["B02"])
    colors["B03"] = hexToBGR(colors["B03"])
    colors["B04"] = hexToBGR(colors["B04"])
    colors["B05"] = hexToBGR(colors["B05"])
    colors["B06"] = hexToBGR(colors["B06"])
    colors["B07"] = hexToBGR(colors["B07"])
    colors["B08"] = hexToBGR(colors["B08"])
    colors["B09"] = hexToBGR(colors["B09"])
    colors["B0A"] = hexToBGR(colors["B0A"])
    colors["B0B"] = hexToBGR(colors["B0B"])
    colors["B0C"] = hexToBGR(colors["B0C"])
    colors["B0D"] = hexToBGR(colors["B0D"])
    colors["B0E"] = hexToBGR(colors["B0E"])
    colors["B0F"] = hexToBGR(colors["B0F"])

    colors["red"]       = colors["B08"]
    colors["orange"]    = colors["B09"]
    colors["yellow"]    = colors["B0A"]
    colors["green"]     = colors["B0B"]
    colors["teal"]      = colors["B0C"]
    colors["blue"]      = colors["B0D"]
    colors["purple"]    = colors["B0E"]
    colors["themed"]    = colors["B0F"]

    return colors

def parseScheme(colors):
    return {

        'Booleans': {
            'caretLineVisible': True,
            'preferFixed': True,
            'useSelFore': False
        },

        'CommonStyles': {
            'attribute name': {
                'fore': colors["orange"]
            },
            'attribute value': {
                'fore': colors["green"]
            },
            'bracebad': {
                'fore': colors["baseForeBlend1"]
            },
            'bracehighlight': {
                'fore': colors["baseForeBlend1"],
                'back': colors["baseBackBlend2"]
            },
            'classes': {
                'fore': colors["yellow"]
            },
            'comments': {
                'fore': colors["comment"],
                'italic': True
            },
            'control characters': {
                'fore': colors["orange"]
            },
            'default_fixed': {
                'back': colors["baseBack"],
                'eolfilled': 0,
                'face': '"Source Code Pro", Consolas, Inconsolata, "DejaVu Sans Mono", "Bitstream Vera Sans Mono", Menlo, Monaco, "Courier New", Courier, Monospace',
                'fore': colors["baseFore"],
                'hotspot': 0,
                'italic': 0,
                'size': 11,
                'useFixed': 1,
                'bold': 0,
                'lineSpacing': 2
            },
            'default_proportional': {
                'back': colors["baseBack"],
                'eolfilled': 0,
                'face': '"DejaVu Sans", "Bitstream Vera Sans", Helvetica, Tahoma, Verdana, sans-serif',
                'fore': colors["baseFore"],
                'hotspot': 0,
                'italic': 0,
                'size': 11,
                'useFixed': 0,
                'bold': 0,
                'lineSpacing': 2
            },
            'fold markers': {
                'fore': colors["comment"],
                'back': colors["baseBack"]
            },
            'functions': {
                'fore': colors["blue"]
            },
            'identifiers': {
                'fore': colors["baseForeBlend1"]
            },
            'indent guides': {
                'fore': colors["baseBackBlend1"]
            },
            'keywords': {
                'fore': colors["purple"]
            },
            'keywords2': {
                'fore': colors["red"]
            },
            'linenumbers': {
                'back': colors["baseBackBlend1"],
                'fore': colors["baseBackBlend3"],
                'size': 10,
                'useFixed': True,
                'bold': False
            },
            'numbers': {
                'fore': colors["orange"]
            },
            'operators': {
                'fore': colors["blue"]
            },
            'preprocessor': {
                'fore': colors["baseForeBlend1"]
            },
            'regex': {
                'fore': colors["teal"]
            },
            'stderr': {
                'fore': colors["red"]
            },
            'stdin': {
                'fore': colors["orange"]
            },
            'stdout': {
                'fore': colors["teal"]
            },
            'stringeol': {
                'back': colors["baseForeBlend2"],
                'eolfilled': True
            },
            'strings': {
                'fore': colors["green"]
            },
            'tags': {
                'fore': colors["red"]
            },
            'variables': {
                'fore': colors["red"]
            }
        },

        'LanguageStyles': {
            'CSS': {
                'ids': {
                    'fore': colors["purple"]
                },
                'values': {
                    'fore': colors["green"]
                }
            },
            'Diff': {
                'additionline': {
                    'fore': colors["green"]
                },
                'chunkheader': {
                    'fore': colors["baseForeBlend2"]
                },
                'deletionline': {
                    'fore': colors["red"]
                },
                'diffline': {
                    'fore': colors["yellow"]
                },
                'fileline': {
                    'fore': colors["baseFore"]
                }
            },
            'Errors': {
                'Error lines': {
                    'fore': colors["red"],
                    'hotspot': 1,
                    'italic': 1
                }
            },
            'HTML': {
                'attributes': {
                    'fore': colors["green"]
                },
                'cdata': {
                    'fore': colors["orange"]
                },
                'cdata content': {
                    'fore': colors["baseFore"]
                },
                'cdata tags': {
                    'fore': colors["baseForeBlend1"]
                },
                'xpath attributes': {
                    'fore': colors["teal"]
                }
            },
            'HTML5': {
                'attributes': {
                    'fore': colors["green"]
                },
                'cdata': {
                    'fore': colors["orange"]
                },
                'cdata content': {
                    'fore': colors["baseFore"]
                },
                'cdata tags': {
                    'fore': colors["baseForeBlend1"]
                },
                'xpath attributes': {
                    'fore': colors["teal"]
                }
            },
            'XML': {
                'attributes': {
                    'fore': colors["green"]
                },
                'cdata': {
                    'fore': colors["orange"]
                },
                'cdata content': {
                    'fore': colors["baseFore"]
                },
                'cdata tags': {
                    'fore': colors["baseForeBlend1"]
                },
                'xpath attributes': {
                    'fore': colors["teal"]
                }
            },
            'JavaScript': {
                'commentdockeyword': {
                    'fore': colors["commentBlend"]
                },
                'commentdockeyworderror': {
                    'fore': colors["red"]
                },
                'globalclass': {
                    'fore': colors["yellow"]
                }
            },
            'PHP': {
                'commentdockeyword': {
                    'fore': colors["commentBlend"]
                },
                'commentdockeyworderror': {
                    'fore': colors["red"]
                }
            }
        },

        'MiscLanguageSettings': {},

        'Colors': {
            'bookmarkColor': colors["baseBackBlend2"],
            'callingLineColor': colors["baseBackBlend1"],
            'caretFore': colors["commentBlend"],
            'caretLineBack': colors["baseBackBlend1"],
            'changeMarginDeleted': colors["red"],
            'changeMarginInserted': colors["green"],
            'changeMarginReplaced': colors["blue"],
            'currentLineColor': colors["baseBackBlend1"],
            'edgeColor': colors["baseBackBlend1"],
            'foldMarginColor': colors["baseBack"],
            'selBack': colors["baseBackBlend2"],
            'selFore': colors["baseFore"],
            'whitespaceColor': colors["baseBackBlend2"]
        },

        'Indicators': {
            'collab_local_change': {
                'alpha': 0,
                'color': colors["green"],
                'draw_underneath': False,
                'style': 5
            },
            'collab_remote_change': {
                'alpha': 255,
                'color': colors["yellow"],
                'draw_underneath': True,
                'style': 7
            },
            'collab_remote_cursor_1': {
                'alpha': 255,
                'color': colors["yellow"],
                'draw_underneath': True,
                'style': 6
            },
            'collab_remote_cursor_2': {
                'alpha': 255,
                'color': colors["orange"],
                'draw_underneath': True,
                'style': 6
            },
            'collab_remote_cursor_3': {
                'alpha': 255,
                'color': colors["red"],
                'draw_underneath': True,
                'style': 6
            },
            'collab_remote_cursor_4': {
                'alpha': 255,
                'color': colors["blue"],
                'draw_underneath': True,
                'style': 6
            },
            'collab_remote_cursor_5': {
                'alpha': 255,
                'color': colors["teal"],
                'draw_underneath': True,
                'style': 6
            },
            'find_highlighting': {
                'alpha': 100,
                'color': colors["baseBackBlend2"],
                'draw_underneath': True,
                'style': 7
            },
            'linter_error': {
                'alpha': 255,
                'color': colors["red"],
                'draw_underneath': True,
                'style': 13
            },
            'linter_warning': {
                'alpha': 255,
                'color': colors["yellow"],
                'draw_underneath': True,
                'style': 13
            },
            'multiple_caret_area': {
                'alpha': 255,
                'color': colors["blue"],
                'draw_underneath': False,
                'style': 6
            },
            'soft_characters': {
                'alpha': 255,
                'color': colors["baseForeBlend2"],
                'draw_underneath': False,
                'style': 0
            },
            'tabstop_current': {
                'alpha': 255,
                'color': colors["baseBackBlend1"],
                'draw_underneath': True,
                'style': 7
            },
            'tabstop_pending': {
                'alpha': 255,
                'color': colors["baseBackBlend2"],
                'draw_underneath': True,
                'style': 6
            },
            'tag_matching': {
                'alpha': 255,
                'color': colors["blue"],
                'draw_underneath': False,
                'style': 0
            }
        }

    }
