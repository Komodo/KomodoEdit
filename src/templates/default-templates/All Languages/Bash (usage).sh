#!/bin/sh

############################################################
#  Program:
#  Author :
############################################################


## BEGIN SCRIPT
usage()
{
    cat << EOF

usage: $0 OPTIONS

OPTIONS can be:
    -h      Show this message
    -f      Filename
    -v      Verbose (boolean)

EOF
}

# Show usage when there are no arguments.
if test -z "$1"
then
    usage
    exit
fi

VERBOSE=
FILENAME=

# Check options passed in.
while getopts "h f:v" OPTION
do
    case $OPTION in
        h)
            usage
            exit 1
            ;;
        f)
            FILENAME=$OPTARG
            ;;
        v)
            VERBOSE=1
            ;;
        ?)
            usage
            exit
            ;;
    esac
done

# Do something with the arguments...

## END SCRIPT
