import json
import sys

with open(sys.argv[1], "r") as ins:
    for line in ins:
        line = json.loads(line)
        [timestamp, command, value] = line
        
        if command == "build_output":
            print value["line"]
        else:
            print "\n%s: %s\n" % (command, value)
