"""
Tests for account lockout functionality
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import AccountLockout


class TestAccountLockout:
    """Test account lockout functionality"""
    
    @pytest.mark.asyncio
    async def test_record_failed_attempt(self):
        """Test recording failed login attempts"""
        with patch('app.core.cache.cache.get', new_callable=AsyncMock) as mock_get:
            with patch('app.core.cache.cache.set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None
                
                await AccountLockout.record_failed_attempt("testuser")
                
                # Check that attempt was recorded
                mock_set.assert_called()
                call_args = mock_set.call_args
                assert "lockout:user:testuser:attempts" in call_args[0][0]
                assert call_args[0][1] == "1"
    
    @pytest.mark.asyncio
    async def test_account_lockout_after_max_attempts(self):
        """Test account gets locked after max attempts"""
        with patch('app.core.cache.cache.get', new_callable=AsyncMock) as mock_get:
            with patch('app.core.cache.cache.set', new_callable=AsyncMock) as mock_set:
                # Simulate 4 previous attempts
                mock_get.side_effect = lambda key: "4" if "attempts" in key else None
                
                await AccountLockout.record_failed_attempt("testuser")
                
                # Check that account was locked
                calls = mock_set.call_args_list
                lock_call = next((call for call in calls if "locked" in call[0][0]), None)
                assert lock_call is not None
                assert lock_call[0][1] == "1"
    
    @pytest.mark.asyncio
    async def test_is_locked_check(self):
        """Test checking if account is locked"""
        with patch('app.core.cache.cache.get', new_callable=AsyncMock) as mock_get:
            # Test locked account
            mock_get.return_value = "1"
            assert await AccountLockout.is_locked("testuser") is True
            
            # Test unlocked account
            mock_get.return_value = None
            assert await AccountLockout.is_locked("testuser") is False
    
    @pytest.mark.asyncio
    async def test_clear_failed_attempts(self):
        """Test clearing failed attempts after successful login"""
        with patch('app.core.cache.cache.delete', new_callable=AsyncMock) as mock_delete:
            await AccountLockout.clear_failed_attempts("testuser")
            
            mock_delete.assert_called_once()
            assert "lockout:user:testuser:attempts" in mock_delete.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_progressive_lockout(self):
        """Test progressive lockout duration increases"""
        with patch('app.core.cache.cache.get', new_callable=AsyncMock) as mock_get:
            with patch('app.core.cache.cache.set', new_callable=AsyncMock) as mock_set:
                # Simulate previous lockout
                mock_get.side_effect = lambda key: "5" if "attempts" in key else "2" if "count" in key else None
                
                await AccountLockout.record_failed_attempt("testuser")
                
                # Check that lockout duration increased
                lock_call = next((call for call in mock_set.call_args_list if "locked" in call[0][0]), None)
                assert lock_call is not None
                # Duration should be longer than base duration