"""Allow cronwrap to be invoked as `python -m cronwrap`."""

import sys
from cronwrap.cli import main

if __name__ == "__main__":
    sys.exit(main())
