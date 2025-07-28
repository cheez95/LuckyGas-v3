"""Chunghwa Telecom SMS provider implementation for Taiwan local SMS."""
import logging
import aiohttp
import hashlib
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

from app.core.config import settings
from app.models.notification import NotificationStatus

logger = logging.getLogger(__name__)


class ChunghwaProvider:
    """
    Chunghwa Telecom (中華電信) SMS provider for Taiwan
    Production-ready implementation with CHT SMS API
    """
    
    def __init__(self):
        self.account_id = settings.CHT_SMS_ACCOUNT_ID
        self.password = settings.CHT_SMS_PASSWORD
        self.api_url = settings.CHT_SMS_API_URL or "https://api.emome.net/SMS/SendSMS"
        self.status_url = settings.CHT_SMS_STATUS_URL or "https://api.emome.net/SMS/QueryStatus"
        
        # Connection pool
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Performance metrics
        self.total_sent = 0
        self.total_failed = 0
        self.last_error = None
        
    async def initialize(self):
        """Initialize provider with connection pool"""
        connector = aiohttp.TCPConnector(
            limit=50,  # Total connection pool size
            limit_per_host=20,  # Per-host connection limit
            ttl_dns_cache=300  # DNS cache timeout
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        logger.info("Chunghwa Telecom provider initialized with connection pooling")
        
    async def send_sms(
        self,
        phone: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS via Chunghwa Telecom
        
        Args:
            phone: Recipient phone number (Taiwan format)
            message: Message content (supports Traditional Chinese)
            metadata: Additional tracking data
            
        Returns:
            Dict with success status, message_id, cost, segments
        """
        if not self._session:
            await self.initialize()
            
        try:
            # Format phone for Taiwan (remove country code if present)
            if phone.startswith("+886"):
                phone = "0" + phone[4:]
            elif phone.startswith("886"):
                phone = "0" + phone[3:]
            elif not phone.startswith("0"):
                phone = "0" + phone
                
            # Validate Taiwan mobile number format
            if not (phone.startswith("09") and len(phone) == 10):
                return {
                    "success": False,
                    "error": f"Invalid Taiwan mobile number format: {phone}"
                }
                
            # Calculate segments
            segments = self._calculate_segments(message)
            
            # Generate message ID and timestamp
            timestamp = int(time.time())
            msg_id = f"LG{timestamp}{phone[-4:]}"
            
            # Create signature for authentication
            signature = self._create_signature(timestamp)
            
            # Prepare XML request (CHT uses XML format)
            xml_data = self._build_send_xml(
                phone=phone,
                message=message,
                msg_id=msg_id,
                timestamp=timestamp,
                signature=signature
            )
            
            headers = {
                "Content-Type": "application/xml; charset=UTF-8",
                "Accept": "application/xml"
            }
            
            # Send request
            async with self._session.post(
                self.api_url,
                data=xml_data.encode('utf-8'),
                headers=headers
            ) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    # Parse XML response
                    result = self._parse_send_response(response_text)
                    
                    if result["success"]:
                        self.total_sent += 1
                        
                        # Calculate cost (CHT charges per segment)
                        cost_per_segment = 0.7  # TWD per segment for bulk rate
                        total_cost = segments * cost_per_segment
                        
                        return {
                            "success": True,
                            "message_id": result["msg_id"],
                            "segments": segments,
                            "cost": total_cost,
                            "provider_response": {
                                "credit_used": result.get("credit_used"),
                                "credit_remaining": result.get("credit_remaining")
                            }
                        }
                    else:
                        self.total_failed += 1
                        self.last_error = result.get("error", "Unknown error")
                        
                        return {
                            "success": False,
                            "error": self.last_error,
                            "error_code": result.get("error_code")
                        }
                else:
                    self.total_failed += 1
                    self.last_error = f"HTTP {response.status}: {response_text}"
                    
                    return {
                        "success": False,
                        "error": self.last_error
                    }
                    
        except aiohttp.ClientError as e:
            self.total_failed += 1
            self.last_error = f"Network error: {str(e)}"
            logger.error(f"Chunghwa network error: {e}")
            
            return {
                "success": False,
                "error": self.last_error
            }
            
        except Exception as e:
            self.total_failed += 1
            self.last_error = str(e)
            logger.error(f"Chunghwa unexpected error: {e}")
            
            return {
                "success": False,
                "error": self.last_error
            }
            
    async def check_status(self, message_id: str) -> Dict[str, Any]:
        """Check message delivery status"""
        if not self._session:
            await self.initialize()
            
        try:
            timestamp = int(time.time())
            signature = self._create_signature(timestamp)
            
            # Build status query XML
            xml_data = self._build_status_xml(
                msg_id=message_id,
                timestamp=timestamp,
                signature=signature
            )
            
            headers = {
                "Content-Type": "application/xml; charset=UTF-8",
                "Accept": "application/xml"
            }
            
            async with self._session.post(
                self.status_url,
                data=xml_data.encode('utf-8'),
                headers=headers
            ) as response:
                if response.status == 200:
                    response_text = await response.text()
                    result = self._parse_status_response(response_text)
                    
                    if result["success"]:
                        # Map CHT status to our status enum
                        status_map = {
                            "0": NotificationStatus.DELIVERED,  # 已送達
                            "1": NotificationStatus.SENT,       # 發送中
                            "2": NotificationStatus.PENDING,    # 等待中
                            "3": NotificationStatus.FAILED,     # 發送失敗
                            "4": NotificationStatus.FAILED      # 無法送達
                        }
                        
                        cht_status = result.get("status_code", "2")
                        our_status = status_map.get(cht_status, NotificationStatus.PENDING)
                        
                        return {
                            "success": True,
                            "status": our_status,
                            "provider_status": result.get("status_text"),
                            "delivery_time": result.get("delivery_time")
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Failed to check status")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            logger.error(f"Error checking Chunghwa message status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check by checking account balance"""
        if not self._session:
            await self.initialize()
            
        try:
            timestamp = int(time.time())
            signature = self._create_signature(timestamp)
            
            # Build balance query XML
            xml_data = self._build_balance_xml(timestamp, signature)
            
            headers = {
                "Content-Type": "application/xml; charset=UTF-8",
                "Accept": "application/xml"
            }
            
            async with self._session.post(
                self.api_url.replace("SendSMS", "QueryBalance"),
                data=xml_data.encode('utf-8'),
                headers=headers
            ) as response:
                if response.status == 200:
                    response_text = await response.text()
                    result = self._parse_balance_response(response_text)
                    
                    if result["success"]:
                        balance = result.get("balance", 0)
                        is_healthy = balance > 100  # Minimum balance threshold
                        
                        return {
                            "healthy": is_healthy,
                            "balance": balance,
                            "success_rate": (
                                self.total_sent / (self.total_sent + self.total_failed)
                                if (self.total_sent + self.total_failed) > 0
                                else 1.0
                            ),
                            "last_error": self.last_error
                        }
                    else:
                        return {
                            "healthy": False,
                            "error": result.get("error"),
                            "last_error": self.last_error
                        }
                else:
                    return {
                        "healthy": False,
                        "error": f"HTTP {response.status}",
                        "last_error": self.last_error
                    }
                    
        except Exception as e:
            logger.error(f"Chunghwa health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "last_error": self.last_error
            }
            
    async def register_delivery_callback(self, message_id: str, callback_url: str) -> bool:
        """
        Register webhook for delivery updates
        Note: CHT requires callback URL to be pre-configured in account settings
        """
        # Chunghwa Telecom requires webhook URLs to be configured in account settings
        # Cannot dynamically register per message
        logger.info(f"CHT requires pre-configured webhooks, cannot set for {message_id}")
        return False
        
    def _create_signature(self, timestamp: int) -> str:
        """Create authentication signature"""
        # CHT uses MD5 hash of account_id + password + timestamp
        signature_string = f"{self.account_id}{self.password}{timestamp}"
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()
        
    def _calculate_segments(self, message: str) -> int:
        """Calculate number of SMS segments for message"""
        # Chinese characters count as 2 bytes in CHT system
        byte_count = 0
        for char in message:
            if ord(char) > 127:
                byte_count += 2  # Chinese character
            else:
                byte_count += 1  # ASCII character
                
        # CHT limits: 70 bytes for single segment, 67 bytes for multi-segment
        if byte_count <= 70:
            return 1
        else:
            return ((byte_count - 1) // 67) + 1
            
    def _build_send_xml(
        self,
        phone: str,
        message: str,
        msg_id: str,
        timestamp: int,
        signature: str
    ) -> str:
        """Build XML request for sending SMS"""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<SmsMessage>
    <Account>{self.account_id}</Account>
    <Signature>{signature}</Signature>
    <Timestamp>{timestamp}</Timestamp>
    <MessageId>{msg_id}</MessageId>
    <Recipient>{phone}</Recipient>
    <Message><![CDATA[{message}]]></Message>
    <Type>N</Type>
    <Encoding>UTF8</Encoding>
</SmsMessage>"""
        return xml
        
    def _build_status_xml(self, msg_id: str, timestamp: int, signature: str) -> str:
        """Build XML request for status query"""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<StatusQuery>
    <Account>{self.account_id}</Account>
    <Signature>{signature}</Signature>
    <Timestamp>{timestamp}</Timestamp>
    <MessageId>{msg_id}</MessageId>
</StatusQuery>"""
        return xml
        
    def _build_balance_xml(self, timestamp: int, signature: str) -> str:
        """Build XML request for balance query"""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BalanceQuery>
    <Account>{self.account_id}</Account>
    <Signature>{signature}</Signature>
    <Timestamp>{timestamp}</Timestamp>
</BalanceQuery>"""
        return xml
        
    def _parse_send_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse XML response from send SMS"""
        try:
            root = ET.fromstring(xml_response)
            
            status = root.find("Status")
            if status is not None and status.text == "0":
                return {
                    "success": True,
                    "msg_id": root.find("MessageId").text,
                    "credit_used": int(root.find("CreditUsed").text or 0),
                    "credit_remaining": int(root.find("CreditRemaining").text or 0)
                }
            else:
                error_code = root.find("ErrorCode").text if root.find("ErrorCode") is not None else "Unknown"
                error_msg = self._get_error_message(error_code)
                
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": error_code
                }
                
        except Exception as e:
            logger.error(f"Failed to parse CHT response: {e}")
            return {
                "success": False,
                "error": f"Response parse error: {str(e)}"
            }
            
    def _parse_status_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse XML response from status query"""
        try:
            root = ET.fromstring(xml_response)
            
            status = root.find("Status")
            if status is not None and status.text == "0":
                return {
                    "success": True,
                    "status_code": root.find("DeliveryStatus").text,
                    "status_text": root.find("StatusText").text,
                    "delivery_time": root.find("DeliveryTime").text
                }
            else:
                return {
                    "success": False,
                    "error": "Status query failed"
                }
                
        except Exception as e:
            logger.error(f"Failed to parse CHT status response: {e}")
            return {
                "success": False,
                "error": f"Response parse error: {str(e)}"
            }
            
    def _parse_balance_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse XML response from balance query"""
        try:
            root = ET.fromstring(xml_response)
            
            status = root.find("Status")
            if status is not None and status.text == "0":
                return {
                    "success": True,
                    "balance": int(root.find("Balance").text or 0)
                }
            else:
                return {
                    "success": False,
                    "error": "Balance query failed"
                }
                
        except Exception as e:
            logger.error(f"Failed to parse CHT balance response: {e}")
            return {
                "success": False,
                "error": f"Response parse error: {str(e)}"
            }
            
    def _get_error_message(self, error_code: str) -> str:
        """Get human-readable error message for CHT error codes"""
        error_messages = {
            "1": "認證失敗",
            "2": "帳號錯誤",
            "3": "密碼錯誤",
            "4": "餘額不足",
            "5": "手機號碼格式錯誤",
            "6": "簡訊內容為空",
            "7": "簡訊內容過長",
            "8": "發送時間格式錯誤",
            "9": "預約時間已過期",
            "10": "系統錯誤",
            "11": "IP未授權",
            "12": "帳號已停用"
        }
        
        return error_messages.get(error_code, f"未知錯誤 (代碼: {error_code})")
        
    async def close(self):
        """Close connection pool"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Chunghwa Telecom provider connection pool closed")