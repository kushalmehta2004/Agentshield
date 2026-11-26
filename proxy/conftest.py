import sys
from pathlib import Path

# Make repo-root packages (agent/, eval/) importable when running from proxy/
sys.path.insert(0, str(Path(__file__).parent.parent))
