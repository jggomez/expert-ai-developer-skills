"""What PyInstaller freezes: the installed package holds all the code."""

import sys

from agent_meter.app.desktop import main

sys.exit(main())
