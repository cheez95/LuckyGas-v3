"""
API testing utilities
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json
import jwt
from httpx import AsyncClient, Response

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import UserRole


class APITestClient:
    """Enhanced test client for API testing"""

    def __init__(self, client: AsyncClient, base_url: str = ""):
        self.client = client
        self.base_url = base_url
        self.auth_headers = {}

    def set_auth_token(self, token: str):
        """Set authentication token"""
        self.auth_headers = {"Authorization": f"Bearer {token}"}

    def set_auth_user(self, username: str, role: UserRole):
        """Set authentication for a specific user"""
        token = create_access_token(data={"sub": username, "role": role.value})
        self.set_auth_token(token)

    def clear_auth(self):
        """Clear authentication"""
        self.auth_headers = {}

    async def get(self, url: str, **kwargs) -> Response:
        """GET request with authentication"""
        headers = {**self.auth_headers, **kwargs.get("headers", {})}
        kwargs["headers"] = headers
        return await self.client.get(f"{self.base_url}{url}", **kwargs)

    async def post(self, url: str, **kwargs) -> Response:
        """POST request with authentication"""
        headers = {**self.auth_headers, **kwargs.get("headers", {})}
        kwargs["headers"] = headers
        return await self.client.post(f"{self.base_url}{url}", **kwargs)

    async def put(self, url: str, **kwargs) -> Response:
        """PUT request with authentication"""
        headers = {**self.auth_headers, **kwargs.get("headers", {})}
        kwargs["headers"] = headers
        return await self.client.put(f"{self.base_url}{url}", **kwargs)

    async def patch(self, url: str, **kwargs) -> Response:
        """PATCH request with authentication"""
        headers = {**self.auth_headers, **kwargs.get("headers", {})}
        kwargs["headers"] = headers
        return await self.client.patch(f"{self.base_url}{url}", **kwargs)

    async def delete(self, url: str, **kwargs) -> Response:
        """DELETE request with authentication"""
        headers = {**self.auth_headers, **kwargs.get("headers", {})}
        kwargs["headers"] = headers
        return await self.client.delete(f"{self.base_url}{url}", **kwargs)

    async def paginated_get(
        self, url: str, page: int = 1, size: int = 20, **kwargs
    ) -> Response:
        """GET request with pagination parameters"""
        params = kwargs.get("params", {})
        params.update({"page": page, "size": size})
        kwargs["params"] = params
        return await self.get(url, **kwargs)

    async def get_all_pages(self, url: str, size: int = 20, **kwargs) -> List[Any]:
        """Get all items from a paginated endpoint"""
        all_items = []
        page = 1

        while True:
            response = await self.paginated_get(url, page=page, size=size, **kwargs)
            data = response.json()

            items = data.get("items", [])
            all_items.extend(items)

            if not items or len(items) < size:
                break

            page += 1

        return all_items


class APIResponseValidator:
    """Utility for validating API responses"""

    @staticmethod
    def assert_success(response: Response, status_code: int = 200):
        """Assert response is successful"""
        assert (
            response.status_code == status_code
        ), f"Expected status {status_code}, got {response.status_code}: {response.text}"

    @staticmethod
    def assert_error(response: Response, status_code: int, error_message: str = None):
        """Assert response is an error"""
        assert (
            response.status_code == status_code
        ), f"Expected status {status_code}, got {response.status_code}"

        if error_message:
            data = response.json()
            assert error_message in data.get(
                "detail", ""
            ), f"Expected error message '{error_message}' not found in response"

    @staticmethod
    def assert_pagination(response: Response):
        """Assert response has proper pagination structure"""
        data = response.json()
        assert "items" in data, "Response missing 'items' field"
        assert "total" in data, "Response missing 'total' field"
        assert "page" in data, "Response missing 'page' field"
        assert "size" in data, "Response missing 'size' field"
        assert "pages" in data, "Response missing 'pages' field"

    @staticmethod
    def assert_item_in_list(response: Response, field: str, value: Any):
        """Assert an item with specific field value exists in response list"""
        data = response.json()
        items = data.get("items", data if isinstance(data, list) else [])

        found = any(item.get(field) == value for item in items)
        assert found, f"No item found with {field}={value}"

    @staticmethod
    def assert_fields_present(response: Response, required_fields: List[str]):
        """Assert response contains all required fields"""
        data = response.json()
        if isinstance(data, list):
            data = data[0] if data else {}

        missing_fields = [field for field in required_fields if field not in data]
        assert not missing_fields, f"Missing required fields: {missing_fields}"


def create_test_token(
    username: str = "testuser",
    role: UserRole = UserRole.OFFICE_STAFF,
    expires_in_minutes: int = 30,
) -> str:
    """Create a test JWT token"""
    return create_access_token(
        data={"sub": username, "role": role.value},
        expires_delta=timedelta(minutes=expires_in_minutes),
    )


def decode_token(token: str) -> Dict[str, Any]:
    """Decode JWT token for testing"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


class MockExternalAPI:
    """Mock external API responses for testing"""

    @staticmethod
    def mock_google_routes_response():
        """Mock Google Routes API response"""
        return {
            "routes": [
                {
                    "distanceMeters": 15000,
                    "duration": "2400s",
                    "polyline": {"encodedPolyline": "mock_polyline_data"},
                    "legs": [
                        {
                            "distanceMeters": 5000,
                            "duration": "800s",
                            "endLocation": {
                                "latLng": {"latitude": 25.033, "longitude": 121.565}
                            },
                        }
                    ],
                }
            ]
        }

    @staticmethod
    def mock_vertex_ai_response():
        """Mock Vertex AI prediction response"""
        return {
            "predictions": [
                {
                    "customer_id": 1,
                    "predicted_quantity": 3,
                    "confidence": 0.85,
                    "prediction_date": datetime.now().isoformat(),
                }
            ],
            "model_version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def mock_sms_gateway_response():
        """Mock SMS gateway response"""
        return {
            "message_id": "SMS123456789",
            "status": "sent",
            "recipient": "+886912345678",
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def mock_einvoice_response():
        """Mock e-invoice API response"""
        return {
            "invoice_number": "AA12345678",
            "status": "issued",
            "issue_date": datetime.now().isoformat(),
            "qr_code": "mock_qr_code_data",
        }


async def assert_websocket_message(
    websocket, expected_type: str, timeout: float = 5.0
) -> Dict[str, Any]:
    """Assert a WebSocket message is received with expected type"""
    import asyncio

    try:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
        assert (
            message.get("type") == expected_type
        ), f"Expected message type '{expected_type}', got '{message.get('type')}'"
        return message
    except asyncio.TimeoutError:
        raise AssertionError(f"No WebSocket message received within {timeout} seconds")


def create_form_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create form data for multipart requests"""
    form_data = {}
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            form_data[key] = json.dumps(value)
        else:
            form_data[key] = str(value)
    return form_data
