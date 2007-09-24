#!python
# Run a number of cases of 'measure_lint_leak.py'

import os, time

timeStamp = int(time.time())
desc = "linting-off"
runs = [
        {'desc': 'ko11-python-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.py',
         'komodo': r'C:\Program Files\Komodo-1.1\komodo.exe',
        },
        {'desc': 'ko11-perl-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.pl',
         'komodo': r'C:\Program Files\Komodo-1.1\komodo.exe',
        },
        {'desc': 'ko11-xml-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.xml',
         'komodo': r'C:\Program Files\Komodo-1.1\komodo.exe',
        },
        {'desc': 'ko12-python-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.py',
         'komodo': r'C:\Program Files\Komodo-1.2\komodo.exe',
        },
        {'desc': 'ko12-perl-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.pl',
         'komodo': r'C:\Program Files\Komodo-1.2\komodo.exe',
        },
        {'desc': 'ko12-xml-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.xml',
         'komodo': r'C:\Program Files\Komodo-1.2\komodo.exe',
        },
       ]

#logDir = r"\\crimper\apps\Komodo\stuff\trents_metric_logs\measure_lint_leak\"
cmdTemplate = r'python measure_lint_leak.py --komodo="%(komodo)s" %(file)s > measure_lint_leak.%(desc)s.log'

for run in runs:
    cmd = cmdTemplate % run
    print "running '%s'..." % cmd
    os.system(cmd)

