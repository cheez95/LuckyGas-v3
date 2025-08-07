"""
Test configuration for service unit tests
"""

import sys
from pathlib import Path


# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# This file allows the service tests to run independently
# without needing the full app setup
