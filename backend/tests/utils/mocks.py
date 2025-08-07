"""
Mock utilities for testing
"""

import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock


class MockService:
    """Base class for mock services"""

    def __init__(self):
        self.call_count = {}
        self.responses = {}
        self.errors = {}

    def set_response(self, method: str, response: Any):
        """Set response for a specific method"""
        self.responses[method] = response

    def set_error(self, method: str, error: Exception):
        """Set error for a specific method"""
        self.errors[method] = error

    def get_call_count(self, method: str) -> int:
        """Get number of times a method was called"""
        return self.call_count.get(method, 0)

    def reset(self):
        """Reset all counters and responses"""
        self.call_count.clear()
        self.responses.clear()
        self.errors.clear()

    def _track_call(self, method: str):
        """Track method call"""
        self.call_count[method] = self.call_count.get(method, 0) + 1

    def _get_response(self, method: str, default: Any = None) -> Any:
        """Get response for method"""
        self._track_call(method)

        if method in self.errors:
            raise self.errors[method]

        return self.responses.get(method, default)


class MockGoogleRoutesService(MockService):
    """Mock Google Routes API service"""

    async def optimize_route(self, stops: List[Dict], **kwargs) -> Dict[str, Any]:
        """Mock route optimization"""
        return self._get_response(
            "optimize_route",
            {
                "total_distance_km": len(stops) * 2.5,
                "total_duration_minutes": len(stops) * 15,
                "optimized_stops": stops,
                "route_polyline": "mock_polyline_"
                + "".join(random.choices(string.ascii_lowercase, k=20)),
                "optimization_score": 0.85,
            },
        )

    async def get_distance_matrix(
        self, origins: List[str], destinations: List[str]
    ) -> Dict[str, Any]:
        """Mock distance matrix"""
        return self._get_response(
            "get_distance_matrix",
            {
                "rows": [
                    {
                        "elements": [
                            {
                                "distance": {
                                    "value": random.randint(1000, 10000),
                                    "text": f"{random.randint(1, 10)} km",
                                },
                                "duration": {
                                    "value": random.randint(300, 1800),
                                    "text": f"{random.randint(5, 30)} mins",
                                },
                                "status": "OK",
                            }
                            for _ in destinations
                        ]
                    }
                    for _ in origins
                ],
                "status": "OK",
            },
        )

    async def geocode_address(self, address: str) -> Dict[str, Any]:
        """Mock geocoding"""
        return self._get_response(
            "geocode_address",
            {
                "lat": 25.033 + random.uniform(-0.1, 0.1),
                "lng": 121.565 + random.uniform(-0.1, 0.1),
                "formatted_address": address,
                "place_id": "place_"
                + "".join(random.choices(string.ascii_letters, k=15)),
            },
        )


class MockVertexAIService(MockService):
    """Mock Vertex AI service"""

    async def predict_order_volume(
        self, customer_ids: List[int], **kwargs
    ) -> Dict[str, Any]:
        """Mock order volume prediction"""
        predictions = []
        for customer_id in customer_ids:
            predictions.append(
                {
                    "customer_id": customer_id,
                    "predicted_quantity": random.randint(1, 5),
                    "confidence": round(random.uniform(0.7, 0.95), 2),
                    "prediction_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "factors": {
                        "historical_average": random.randint(2, 4),
                        "seasonal_factor": round(random.uniform(0.8, 1.2), 2),
                        "recent_trend": random.choice(
                            ["increasing", "stable", "decreasing"]
                        ),
                    },
                }
            )

        return self._get_response(
            "predict_order_volume",
            {
                "predictions": predictions,
                "model_version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def analyze_customer_behavior(self, customer_id: int) -> Dict[str, Any]:
        """Mock customer behavior analysis"""
        return self._get_response(
            "analyze_customer_behavior",
            {
                "customer_id": customer_id,
                "churn_risk": round(random.uniform(0, 0.3), 2),
                "lifetime_value": random.randint(50000, 500000),
                "preferred_delivery_days": random.sample(
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 2
                ),
                "average_order_size": random.randint(2, 10),
                "payment_reliability": round(random.uniform(0.8, 1.0), 2),
            },
        )


class MockSMSService(MockService):
    """Mock SMS service"""

    async def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Mock SMS sending"""
        return self._get_response(
            "send_sms",
            {
                "message_id": "SMS" + "".join(random.choices(string.digits, k=10)),
                "status": "sent",
                "recipient": phone,
                "timestamp": datetime.now().isoformat(),
                "cost": 1.5,
            },
        )

    async def send_bulk_sms(
        self, recipients: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Mock bulk SMS sending"""
        results = []
        for recipient in recipients:
            result = await self.send_sms(recipient["phone"], recipient["message"])
            results.append(result)
        return results

    async def get_sms_status(self, message_id: str) -> Dict[str, Any]:
        """Mock SMS status check"""
        return self._get_response(
            "get_sms_status",
            {
                "message_id": message_id,
                "status": random.choice(["delivered", "pending", "failed"]),
                "delivered_at": (
                    datetime.now().isoformat() if random.random() > 0.2 else None
                ),
                "failure_reason": "Invalid number" if random.random() < 0.1 else None,
            },
        )


class MockEInvoiceService(MockService):
    """Mock e - invoice service"""

    async def issue_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock invoice issuance"""
        return self._get_response(
            "issue_invoice",
            {
                "invoice_number": "AA" + "".join(random.choices(string.digits, k=8)),
                "status": "issued",
                "issue_date": datetime.now().isoformat(),
                "qr_code": "https://einvoice.nat.gov.tw / qrcode/"
                + "".join(random.choices(string.ascii_letters, k=20)),
                "verification_code": "".join(random.choices(string.digits, k=4)),
            },
        )

    async def void_invoice(self, invoice_number: str, reason: str) -> Dict[str, Any]:
        """Mock invoice voiding"""
        return self._get_response(
            "void_invoice",
            {
                "invoice_number": invoice_number,
                "status": "voided",
                "void_date": datetime.now().isoformat(),
                "void_reason": reason,
                "confirmation_number": "VOID"
                + "".join(random.choices(string.digits, k=6)),
            },
        )


class MockRedisClient:
    """Mock Redis client for testing"""

    def __init__(self):
        self.data = {}
        self.expires = {}

    async def get(self, key: str) -> Optional[str]:
        """Get value"""
        if key in self.expires and datetime.now() > self.expires[key]:
            del self.data[key]
            del self.expires[key]
            return None
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int = None) -> bool:
        """Set value with optional expiration"""
        self.data[key] = value
        if ex:
            self.expires[key] = datetime.now() + timedelta(seconds=ex)
        return True

    async def delete(self, key: str) -> bool:
        """Delete key"""
        if key in self.data:
            del self.data[key]
            if key in self.expires:
                del self.expires[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if key in self.expires and datetime.now() > self.expires[key]:
            del self.data[key]
            del self.expires[key]
            return False
        return key in self.data

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        if key in self.data:
            self.expires[key] = datetime.now() + timedelta(seconds=seconds)
            return True
        return False

    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if key not in self.expires:
            return -1

        ttl = (self.expires[key] - datetime.now()).total_seconds()
        if ttl <= 0:
            del self.data[key]
            del self.expires[key]
            return -2

        return int(ttl)

    async def flushdb(self):
        """Clear all data"""
        self.data.clear()
        self.expires.clear()

    async def close(self):
        """Close connection (no - op for mock)"""


def create_mock_websocket():
    """Create a mock WebSocket for testing"""
    mock = AsyncMock()
    mock.accept = AsyncMock()
    mock.send_json = AsyncMock()
    mock.receive_json = AsyncMock()
    mock.close = AsyncMock()

    # Queue for simulating received messages
    mock._message_queue = []

    async def receive_json_side_effect():
        if mock._message_queue:
            return mock._message_queue.pop(0)
        raise Exception("No messages in queue")

    mock.receive_json.side_effect = receive_json_side_effect

    def add_message(message: Dict[str, Any]):
        mock._message_queue.append(message)

    mock.add_message = add_message

    return mock


def create_mock_file_upload(
    filename: str = "test.jpg",
    content: bytes = b"test content",
    content_type: str = "image / jpeg",
):
    """Create a mock file upload"""
    from io import BytesIO

    from fastapi import UploadFile

    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.content_type = content_type
    file.file = BytesIO(content)
    file.read = AsyncMock(return_value=content)
    file.seek = Mock()
    file.close = AsyncMock()

    return file
