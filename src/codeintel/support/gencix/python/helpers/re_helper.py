# re helper

function_overrides = {
    'escape': {'returns': 'str'},
    'findall': {'returns': 'list'},
    'match': {'returns': 'compile().match()'},
    'search': {'returns': 'compile().search()'},
    'split': {'returns': 'list'},
    'sub': {'returns': 'str'},
    'subn': {'returns': 'str'},
}
