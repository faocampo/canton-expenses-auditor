# Ensure project root is on sys.path for test imports like `import tools`.
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
