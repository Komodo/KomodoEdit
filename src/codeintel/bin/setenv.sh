#!/bin/sh
echo Setting up environment for codeintel development.

python support/mkenvconf.py -q
if [ $? -ne 0 ]; then
    echo \*\*\*\*
    echo \* There was an error setting up your environment for codeintel dev.
    echo \* You must correct these errors before continuing.
    echo \*\*\*\*
    return 1
fi

. tmp/envconf.sh
if [ $? -ne 0 ]; then
    echo \*\*\*\*
    echo \* There was an error setting up your environment for codeintel dev.
    echo \* You must correct these errors before continuing.
    echo \*\*\*\*
    return 1
fi

