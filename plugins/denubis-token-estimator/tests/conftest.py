"""Put the loose `scripts/` dir on sys.path so the tests can import the three
estimator modules (verify, mapper, estimate) directly. The token-estimator ships
as scripts rather than an installed package, so there is no entry point to import
through — this mirrors how the /estimate command runs them by path."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
