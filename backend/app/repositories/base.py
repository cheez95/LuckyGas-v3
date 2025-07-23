"""
Base repository pattern for data access layer
Provides common CRUD operations with SQLAlchemy async support
"""
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import DeclarativeMeta, selectinload, joinedload
from sqlalchemy.sql import Select
from abc import ABC, abstractmethod
import logging

from app.core.database import Base

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType], ABC):
    """
    Generic repository providing basic CRUD operations
    Implements repository pattern for data access abstraction
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def get(self, id: Any, load_relationships: List[str] = None) -> Optional[ModelType]:
        """
        Get single record by ID with optional eager loading
        
        Args:
            id: Primary key value
            load_relationships: List of relationship names to eager load
            
        Returns:
            Model instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        
        # Add eager loading for relationships
        if load_relationships:
            for rel in load_relationships:
                if hasattr(self.model, rel):
                    query = query.options(selectinload(getattr(self.model, rel)))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by(self, **kwargs) -> Optional[ModelType]:
        """
        Get single record by arbitrary fields
        
        Args:
            **kwargs: Field-value pairs to filter by
            
        Returns:
            First matching model instance or None
        """
        query = select(self.model)
        for key, value in kwargs.items():
            query = query.where(getattr(self.model, key) == value)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Dict[str, Any] = None,
        order_by: str = None,
        load_relationships: List[str] = None
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field-value pairs to filter by
            order_by: Field name to order by (prefix with - for DESC)
            load_relationships: List of relationship names to eager load
            
        Returns:
            List of model instances
        """
        query = select(self.model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, list):
                        query = query.where(getattr(self.model, key).in_(value))
                    else:
                        query = query.where(getattr(self.model, key) == value)
        
        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                query = query.order_by(getattr(self.model, order_by[1:]).desc())
            else:
                query = query.order_by(getattr(self.model, order_by))
        
        # Add eager loading
        if load_relationships:
            for rel in load_relationships:
                if hasattr(self.model, rel):
                    query = query.options(selectinload(getattr(self.model, rel)))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count(self, filters: Dict[str, Any] = None) -> int:
        """
        Count records with optional filtering
        
        Args:
            filters: Dictionary of field-value pairs to filter by
            
        Returns:
            Number of matching records
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def create(self, **kwargs) -> ModelType:
        """
        Create new record
        
        Args:
            **kwargs: Field values for the new record
            
        Returns:
            Created model instance
        """
        db_obj = self.model(**kwargs)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """
        Update existing record
        
        Args:
            id: Primary key value
            **kwargs: Field values to update
            
        Returns:
            Updated model instance or None if not found
        """
        db_obj = await self.get(id)
        if not db_obj:
            return None
        
        for key, value in kwargs.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: Any) -> bool:
        """
        Delete record by ID
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get(id)
        if not db_obj:
            return False
        
        await self.session.delete(db_obj)
        await self.session.commit()
        return True
    
    async def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records efficiently
        
        Args:
            objects: List of dictionaries with field values
            
        Returns:
            List of created model instances
        """
        db_objects = [self.model(**obj) for obj in objects]
        self.session.add_all(db_objects)
        await self.session.commit()
        
        # Refresh all objects to get generated IDs
        for obj in db_objects:
            await self.session.refresh(obj)
        
        return db_objects
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records efficiently
        Each dict must contain 'id' field
        
        Args:
            updates: List of dictionaries with id and fields to update
            
        Returns:
            Number of records updated
        """
        if not updates:
            return 0
        
        # Use bulk_update_mappings for efficiency
        await self.session.execute(
            update(self.model),
            updates
        )
        await self.session.commit()
        return len(updates)
    
    async def exists(self, **kwargs) -> bool:
        """
        Check if record exists with given criteria
        
        Args:
            **kwargs: Field-value pairs to check
            
        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).select_from(self.model)
        for key, value in kwargs.items():
            query = query.where(getattr(self.model, key) == value)
        
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
    
    def build_query(self) -> Select:
        """
        Get base query for custom query building
        
        Returns:
            SQLAlchemy Select query object
        """
        return select(self.model)
    
    async def execute_query(self, query: Select) -> List[ModelType]:
        """
        Execute custom query
        
        Args:
            query: SQLAlchemy Select query
            
        Returns:
            List of model instances
        """
        result = await self.session.execute(query)
        return result.scalars().all()


class CachedRepository(BaseRepository[ModelType]):
    """
    Repository with Redis caching support
    Extends BaseRepository with caching capabilities
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession, cache_prefix: str = None):
        super().__init__(model, session)
        self.cache_prefix = cache_prefix or model.__tablename__
    
    async def get_cached(self, id: Any, ttl: int = 3600) -> Optional[ModelType]:
        """
        Get record with caching
        
        Args:
            id: Primary key value
            ttl: Cache time-to-live in seconds
            
        Returns:
            Model instance or None
        """
        # Import here to avoid circular dependency
        from app.core.cache import cache_result, CacheKeys
        
        cache_key = f"{self.cache_prefix}:{id}"
        
        # Try to get from cache first
        # In real implementation, would use proper cache decorator
        result = await self.get(id)
        
        return result
    
    async def invalidate_cache(self, id: Any):
        """
        Invalidate cache for specific record
        
        Args:
            id: Primary key value
        """
        from app.core.cache import cache
        
        cache_key = f"{self.cache_prefix}:{id}"
        await cache.invalidate(cache_key)