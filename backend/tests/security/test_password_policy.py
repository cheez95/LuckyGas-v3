"""
Tests for password policy enforcement
"""

import pytest

from app.core.security import PasswordValidator


class TestPasswordPolicy:
    """Test password policy validation"""

    def test_valid_password(self):
        """Test valid password passes all checks"""
        is_valid, errors = PasswordValidator.validate_password("Secure@Pass123")
        assert is_valid is True
        assert len(errors) == 0

    def test_password_too_short(self):
        """Test password length validation"""
        is_valid, errors = PasswordValidator.validate_password("Short1!")
        assert is_valid is False
        assert any("至少需要" in error for error in errors)

    def test_password_missing_uppercase(self):
        """Test uppercase requirement"""
        is_valid, errors = PasswordValidator.validate_password("secure@pass123")
        assert is_valid is False
        assert any("大寫字母" in error for error in errors)

    def test_password_missing_lowercase(self):
        """Test lowercase requirement"""
        is_valid, errors = PasswordValidator.validate_password("SECURE@PASS123")
        assert is_valid is False
        assert any("小寫字母" in error for error in errors)

    def test_password_missing_digit(self):
        """Test digit requirement"""
        is_valid, errors = PasswordValidator.validate_password("Secure@Pass")
        assert is_valid is False
        assert any("數字" in error for error in errors)

    def test_password_missing_special(self):
        """Test special character requirement"""
        is_valid, errors = PasswordValidator.validate_password("SecurePass123")
        assert is_valid is False
        assert any("特殊字元" in error for error in errors)

    def test_password_contains_username(self):
        """Test password should not contain username"""
        is_valid, errors = PasswordValidator.validate_password(
            "User123@Pass", "user123"
        )
        assert is_valid is False
        assert any("使用者名稱" in error for error in errors)

    def test_password_common_pattern(self):
        """Test common password patterns are rejected"""
        is_valid, errors = PasswordValidator.validate_password("Password123!")
        assert is_valid is False
        assert any("常見的不安全模式" in error for error in errors)

    def test_password_low_entropy(self):
        """Test password complexity check"""
        is_valid, errors = PasswordValidator.validate_password("Aaaaaaa1!")
        assert is_valid is False
        assert any("複雜度不足" in error for error in errors)

    @pytest.mark.asyncio
    async def test_password_history(self):
        """Test password history check"""
        # This would need a mock cache setup
