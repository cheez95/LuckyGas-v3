"""
Tests for authentication endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import verify_password


class TestAuth:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email
        assert data["user"]["role"] == test_user.role.value
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, test_user: User):
        """Test login with invalid credentials"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "密碼錯誤" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password"
            }
        )
        assert response.status_code == 401
        assert "使用者不存在" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session: AsyncSession):
        """Test login with inactive user"""
        # Create inactive user
        from app.core.security import get_password_hash
        
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            full_name="Inactive User",
            hashed_password=get_password_hash("password"),
            role=UserRole.OFFICE_STAFF,
            is_active=False
        )
        db_session.add(inactive_user)
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "inactive@example.com",
                "password": "password"
            }
        )
        assert response.status_code == 401
        assert "使用者已被停用" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """Test getting current user information"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role.value
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user: User):
        """Test token refresh"""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test token refresh with invalid token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401


class TestUserManagement:
    """Test user management endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, admin_auth_headers: dict, test_user: User, test_admin: User):
        """Test listing users (admin only)"""
        response = await client.get("/api/v1/auth/users", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # At least test_user and test_admin
        
        # Check that users are in the list
        emails = [user["email"] for user in data]
        assert test_user.email in emails
        assert test_admin.email in emails
    
    @pytest.mark.asyncio
    async def test_list_users_forbidden(self, client: AsyncClient, auth_headers: dict):
        """Test listing users without admin permission"""
        response = await client.get("/api/v1/auth/users", headers=auth_headers)
        assert response.status_code == 403
        assert "權限不足" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_user(self, client: AsyncClient, admin_auth_headers: dict):
        """Test creating a new user (admin only)"""
        new_user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "newpassword",
            "role": UserRole.OFFICE_STAFF.value,
            "is_active": True
        }
        
        response = await client.post(
            "/api/v1/auth/users",
            json=new_user_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == new_user_data["email"]
        assert data["role"] == new_user_data["role"]
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, client: AsyncClient, admin_auth_headers: dict, test_user: User):
        """Test creating a user with existing email"""
        duplicate_user_data = {
            "email": test_user.email,
            "username": "duplicate",
            "full_name": "Duplicate User",
            "password": "password",
            "role": UserRole.OFFICE_STAFF.value,
            "is_active": True
        }
        
        response = await client.post(
            "/api/v1/auth/users",
            json=duplicate_user_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 400
        assert "使用者已存在" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_user(self, client: AsyncClient, admin_auth_headers: dict, test_user: User):
        """Test updating a user (admin only)"""
        update_data = {
            "full_name": "Updated Test User",
            "role": UserRole.MANAGER.value
        }
        
        response = await client.put(
            f"/api/v1/auth/users/{test_user.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["role"] == update_data["role"]
    
    @pytest.mark.asyncio
    async def test_toggle_user_status(self, client: AsyncClient, admin_auth_headers: dict, test_user: User):
        """Test toggling user active status"""
        # Deactivate user
        response = await client.put(
            f"/api/v1/auth/users/{test_user.id}/toggle-status",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        
        # Reactivate user
        response = await client.put(
            f"/api/v1/auth/users/{test_user.id}/toggle-status",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        """Test changing user password"""
        password_data = {
            "current_password": "testpassword",
            "new_password": "newtestpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/change-password",
            json=password_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify new password works
        await db_session.refresh(test_user)
        assert verify_password("newtestpassword", test_user.hashed_password)
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers: dict):
        """Test changing password with wrong current password"""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newtestpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/change-password",
            json=password_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "密碼錯誤" in response.json()["detail"]