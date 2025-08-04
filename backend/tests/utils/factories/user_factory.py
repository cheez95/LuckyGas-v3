"""
User factory for test data generation
"""
from typing import Dict, Any, Optional
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from .base import BaseFactory


class UserFactory(BaseFactory):
    """Factory for creating User instances"""
    
    model = User
    
    async def get_default_data(self) -> Dict[str, Any]:
        """Get default user data"""
        username = self.fake.user_name()
        return {
            "username": username,
            "email": f"{username}@example.com",
            "full_name": self.fake.name(),
            "hashed_password": get_password_hash("password123"),
            "role": UserRole.OFFICE_STAFF,
            "is_active": True,
            "is_verified": True,
            "phone": self.random_phone(),
            "employee_id": f"EMP{self.random_string(6, '0123456789')}",
            "department": "營運部",
            "emergency_contact": self.fake.name(),
            "emergency_phone": self.random_phone(),
            "address": self.random_address(),
            "notes": ""
        }
    
    async def create_admin(self, **kwargs) -> User:
        """Create an admin user"""
        data = {
            "role": UserRole.SUPER_ADMIN,
            "department": "管理部"
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_manager(self, **kwargs) -> User:
        """Create a manager user"""
        data = {
            "role": UserRole.MANAGER,
            "department": "管理部"
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_office_staff(self, **kwargs) -> User:
        """Create an office staff user"""
        data = {
            "role": UserRole.OFFICE_STAFF,
            "department": "營運部"
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_driver(self, **kwargs) -> User:
        """Create a driver user"""
        data = {
            "role": UserRole.DRIVER,
            "department": "配送部",
            "driver_license": f"DL{self.random_string(8, '0123456789')}",
            "vehicle_plate": f"{self.random_string(3, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')}-{self.random_string(4, '0123456789')}"
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_customer_user(self, **kwargs) -> User:
        """Create a customer user"""
        data = {
            "role": UserRole.CUSTOMER,
            "department": None,
            "employee_id": None
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_with_password(self, password: str, **kwargs) -> User:
        """Create a user with a specific password"""
        data = await self.build(**kwargs)
        data["hashed_password"] = get_password_hash(password)
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance
    
    async def create_inactive(self, **kwargs) -> User:
        """Create an inactive user"""
        data = {"is_active": False}
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_unverified(self, **kwargs) -> User:
        """Create an unverified user"""
        data = {"is_verified": False}
        data.update(kwargs)
        return await self.create(**data)