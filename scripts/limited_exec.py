"""Set output resource limits inside a fresh child, then exec an argument array.

Avoids preexec_fn in the threaded research parent. This is not a filesystem sandbox.
"""

import os
import resource
import sys

limit = int(sys.argv[1])
resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
args = sys.argv[2:]
os.execvpe(args[0], args, os.environ)
