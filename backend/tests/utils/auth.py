"""
Authentication test utilities
"""

from httpx import AsyncClient

from app.core.config import settings


async def get_test_token(client: AsyncClient, role: str = "office_staff") -> str:
    """Get test authentication token for specified role"""
    # Test users with different roles
    test_users = {
        "super_admin": {"username": "test_admin", "password": "test_admin_password"},
        "manager": {"username": "test_manager", "password": "test_manager_password"},
        "office_staff": {"username": "test_office", "password": "test_office_password"},
        "driver": {"username": "test_driver", "password": "test_driver_password"},
    }

    if role not in test_users:
        raise ValueError(f"Unknown test role: {role}")

    user_data = test_users[role]

    # Login to get token
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": user_data["username"], "password": user_data["password"]},
    )

    if response.status_code != 200:
        raise Exception(f"Failed to get test token for {role}: {response.text}")

    token_data = response.json()
    return token_data["access_token"]
