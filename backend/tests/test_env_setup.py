"""
Test environment setup to mock external services.
This prevents module-level service initialization errors during testing.
"""
import os
import sys
from unittest.mock import MagicMock, Mock

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["TESTING"] = "true"

# Mock Google Cloud modules before they're imported
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.aiplatform'] = MagicMock()
sys.modules['google.cloud.bigquery'] = MagicMock()
sys.modules['google.cloud.secretmanager'] = MagicMock()
sys.modules['vertexai'] = MagicMock()

# Mock storage client
mock_storage = sys.modules['google.cloud.storage']
mock_storage.Client = MagicMock(return_value=MagicMock())

# Mock Vertex AI
mock_vertex = sys.modules['google.cloud.aiplatform']
mock_vertex.init = MagicMock()
mock_vertex.Model = MagicMock()

# Mock BigQuery
mock_bq = sys.modules['google.cloud.bigquery']
mock_bq.Client = MagicMock(return_value=MagicMock())

# Mock Secret Manager
mock_sm = sys.modules['google.cloud.secretmanager']
mock_sm.SecretManagerServiceClient = MagicMock(return_value=MagicMock())