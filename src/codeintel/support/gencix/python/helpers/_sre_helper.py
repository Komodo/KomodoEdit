# re helper

function_overrides = {
    'compile': {'returns': 'SRE_Pattern'},
    # Override these generated methods.
    'SRE_Pattern.findall': {'returns': 'list'},
    'SRE_Pattern.match': {'returns': 'SRE_Match'},
    'SRE_Pattern.search': {'returns': 'SRE_Match'},
    'SRE_Pattern.split': {'returns': 'list'},
    'SRE_Pattern.sub': {'returns': 'str'},
    'SRE_Pattern.subn': {'returns': 'str'},
}

hidden_classes_exprs = [
    'compile("abc", 0, [1])',                # the hidden "SRE_Pattern" class
    'compile("abc", 0, [1]).search("abc")',  # the hidden "SRE_Match" class
]
