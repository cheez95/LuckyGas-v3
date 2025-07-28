from typing import Dict, Optional, Any
from datetime import datetime
import json
import os
from pathlib import Path

class LocalizationService:
    """
    Backend localization service for Taiwan market
    Handles:
    - API response messages in Traditional Chinese
    - Email templates localization
    - SMS templates
    - Error messages
    - Date/time formatting
    """
    
    def __init__(self):
        self.translations = self._load_translations()
        self.default_locale = 'zh-TW'
        
    def _load_translations(self) -> Dict[str, Dict[str, Any]]:
        """Load translation files"""
        translations = {}
        translations_dir = Path(__file__).parent.parent / 'locales'
        
        if not translations_dir.exists():
            # Create default translations if directory doesn't exist
            translations_dir.mkdir(exist_ok=True)
            self._create_default_translations(translations_dir)
        
        for locale_file in translations_dir.glob('*.json'):
            locale = locale_file.stem
            with open(locale_file, 'r', encoding='utf-8') as f:
                translations[locale] = json.load(f)
                
        return translations
    
    def _create_default_translations(self, translations_dir: Path):
        """Create default Traditional Chinese translations"""
        zh_tw_translations = {
            "errors": {
                "not_found": "找不到請求的資源",
                "unauthorized": "您沒有權限執行此操作",
                "forbidden": "禁止訪問",
                "bad_request": "請求無效",
                "server_error": "伺服器錯誤",
                "validation_error": "資料驗證失敗",
                "duplicate_entry": "資料已存在",
                "database_error": "資料庫錯誤",
                "network_error": "網路連線錯誤",
                "timeout": "請求逾時",
                "order": {
                    "not_found": "訂單不存在",
                    "cannot_modify": "此狀態下無法修改訂單",
                    "cannot_cancel": "此狀態下無法取消訂單",
                    "already_delivered": "訂單已送達",
                    "invalid_status": "無效的訂單狀態"
                },
                "customer": {
                    "not_found": "客戶不存在",
                    "duplicate_code": "客戶代碼已存在",
                    "credit_blocked": "客戶信用額度已封鎖",
                    "inactive": "客戶已停用"
                },
                "auth": {
                    "invalid_credentials": "用戶名或密碼錯誤",
                    "token_expired": "登入已過期，請重新登入",
                    "insufficient_permissions": "權限不足",
                    "account_locked": "帳號已鎖定"
                },
                "route": {
                    "not_found": "路線不存在",
                    "already_assigned": "路線已指派司機",
                    "cannot_modify": "路線進行中，無法修改",
                    "optimization_failed": "路線優化失敗"
                },
                "driver": {
                    "not_found": "司機不存在",
                    "not_available": "司機不可用",
                    "already_on_route": "司機正在配送中"
                },
                "payment": {
                    "insufficient_credit": "信用額度不足",
                    "payment_failed": "付款失敗",
                    "invalid_method": "無效的付款方式"
                }
            },
            "success": {
                "created": "新增成功",
                "updated": "更新成功",
                "deleted": "刪除成功",
                "saved": "儲存成功",
                "order": {
                    "created": "訂單建立成功",
                    "updated": "訂單更新成功",
                    "cancelled": "訂單取消成功",
                    "delivered": "訂單配送完成"
                },
                "customer": {
                    "created": "客戶新增成功",
                    "updated": "客戶資料更新成功",
                    "deleted": "客戶刪除成功"
                },
                "route": {
                    "created": "路線建立成功",
                    "optimized": "路線優化成功",
                    "published": "路線發布成功",
                    "assigned": "司機指派成功"
                },
                "auth": {
                    "login": "登入成功",
                    "logout": "登出成功",
                    "password_changed": "密碼更新成功",
                    "password_reset_sent": "密碼重設郵件已發送"
                }
            },
            "email": {
                "subjects": {
                    "order_confirmation": "訂單確認 - 幸福氣",
                    "delivery_notification": "配送通知 - 幸福氣",
                    "invoice": "電子發票 - 幸福氣",
                    "password_reset": "密碼重設 - 幸福氣",
                    "welcome": "歡迎加入幸福氣",
                    "payment_reminder": "付款提醒 - 幸福氣"
                },
                "templates": {
                    "order_confirmation": """
親愛的 {{customer_name}} 您好，

感謝您的訂購！您的訂單已確認。

訂單編號：{{order_number}}
訂購項目：{{items}}
預計配送日期：{{delivery_date}}
配送地址：{{delivery_address}}

如有任何問題，請聯繫我們的客服團隊。

幸福氣 敬上
""",
                    "delivery_notification": """
親愛的 {{customer_name}} 您好，

您的訂單將於今日配送。

訂單編號：{{order_number}}
配送司機：{{driver_name}}
預計到達時間：{{estimated_time}}

請確保配送地址有人收貨。

幸福氣 敬上
""",
                    "password_reset": """
親愛的 {{user_name}} 您好，

您已申請重設密碼。請點擊以下連結重設您的密碼：

{{reset_link}}

此連結將在24小時後失效。

如果您沒有申請重設密碼，請忽略此郵件。

幸福氣 敬上
"""
                }
            },
            "sms": {
                "order_confirmation": "【幸福氣】訂單{{order_number}}已確認，預計{{delivery_date}}配送。",
                "delivery_today": "【幸福氣】您的訂單今日配送，司機{{driver_name}}將於{{time}}送達。",
                "delivery_completed": "【幸福氣】訂單{{order_number}}已送達，感謝您的訂購！",
                "payment_reminder": "【幸福氣】提醒您訂單{{order_number}}尚未付款，請儘速付款。"
            },
            "status": {
                "order": {
                    "pending": "待處理",
                    "confirmed": "已確認",
                    "assigned": "已指派",
                    "in_delivery": "配送中",
                    "delivered": "已送達",
                    "cancelled": "已取消"
                },
                "payment": {
                    "unpaid": "未付款",
                    "paid": "已付款",
                    "partial": "部分付款",
                    "refunded": "已退款"
                },
                "customer": {
                    "active": "正常",
                    "inactive": "停用",
                    "suspended": "暫停"
                },
                "route": {
                    "draft": "草稿",
                    "published": "已發布",
                    "in_progress": "進行中",
                    "completed": "已完成"
                }
            },
            "notification": {
                "titles": {
                    "order_created": "新訂單",
                    "order_assigned": "訂單指派",
                    "route_published": "路線發布",
                    "delivery_completed": "配送完成",
                    "payment_received": "收到付款",
                    "low_stock": "低庫存警示"
                },
                "messages": {
                    "order_created": "收到新訂單 {{order_number}}",
                    "order_assigned": "訂單 {{order_number}} 已指派給您",
                    "route_published": "新路線已發布，請查看您的配送任務",
                    "delivery_completed": "訂單 {{order_number}} 已完成配送",
                    "payment_received": "已收到訂單 {{order_number}} 的付款",
                    "low_stock": "{{product_name}} 庫存不足，請及時補貨"
                }
            },
            "validation": {
                "required": "此欄位為必填",
                "email_invalid": "請輸入有效的電子郵件",
                "phone_invalid": "請輸入有效的電話號碼",
                "date_invalid": "日期格式不正確",
                "number_invalid": "請輸入數字",
                "min_length": "最少需要 {{min}} 個字元",
                "max_length": "最多 {{max}} 個字元",
                "min_value": "最小值為 {{min}}",
                "max_value": "最大值為 {{max}}",
                "pattern_mismatch": "格式不正確"
            }
        }
        
        # Save translations
        with open(translations_dir / 'zh-TW.json', 'w', encoding='utf-8') as f:
            json.dump(zh_tw_translations, f, ensure_ascii=False, indent=2)
    
    def translate(self, key: str, locale: Optional[str] = None, **kwargs) -> str:
        """Translate a key to the specified locale with variable substitution"""
        locale = locale or self.default_locale
        
        if locale not in self.translations:
            return key
        
        # Navigate through nested keys
        keys = key.split('.')
        value = self.translations[locale]
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return key
        
        if not isinstance(value, str):
            return key
        
        # Replace variables
        for var, val in kwargs.items():
            value = value.replace(f'{{{{{var}}}}}', str(val))
        
        return value
    
    def format_date(self, date: datetime, format_type: str = 'default') -> str:
        """Format date for Taiwan locale"""
        if format_type == 'minguo':
            # Convert to Minguo calendar (ROC year)
            minguo_year = date.year - 1911
            return f"民國{minguo_year}年{date.month:02d}月{date.day:02d}日"
        elif format_type == 'full':
            return date.strftime('%Y年%m月%d日 %H:%M')
        else:
            return date.strftime('%Y/%m/%d')
    
    def format_currency(self, amount: float) -> str:
        """Format currency for Taiwan (NT$)"""
        return f"NT${amount:,.0f}"
    
    def format_phone(self, phone: str) -> str:
        """Format Taiwan phone number"""
        # Remove all non-numeric characters
        cleaned = ''.join(filter(str.isdigit, phone))
        
        # Mobile number (09XX-XXX-XXX)
        if cleaned.startswith('09') and len(cleaned) == 10:
            return f"{cleaned[:4]}-{cleaned[4:7]}-{cleaned[7:]}"
        
        # Landline (0X-XXXX-XXXX)
        elif cleaned.startswith('0') and len(cleaned) >= 9:
            if cleaned[1] in '2345678':  # Major cities
                return f"{cleaned[:2]}-{cleaned[2:6]}-{cleaned[6:]}"
            else:  # Other areas
                return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
        
        return phone
    
    def get_error_message(self, error_type: str, locale: Optional[str] = None, **kwargs) -> str:
        """Get localized error message"""
        return self.translate(f"errors.{error_type}", locale, **kwargs)
    
    def get_success_message(self, action: str, locale: Optional[str] = None, **kwargs) -> str:
        """Get localized success message"""
        return self.translate(f"success.{action}", locale, **kwargs)
    
    def get_email_template(self, template_name: str, locale: Optional[str] = None, **kwargs) -> Dict[str, str]:
        """Get localized email template with subject and body"""
        subject = self.translate(f"email.subjects.{template_name}", locale, **kwargs)
        body = self.translate(f"email.templates.{template_name}", locale, **kwargs)
        
        return {
            "subject": subject,
            "body": body
        }
    
    def get_sms_template(self, template_name: str, locale: Optional[str] = None, **kwargs) -> str:
        """Get localized SMS template"""
        return self.translate(f"sms.{template_name}", locale, **kwargs)
    
    def translate_status(self, status_type: str, status_value: str, locale: Optional[str] = None) -> str:
        """Translate status values"""
        return self.translate(f"status.{status_type}.{status_value}", locale)
    
    def get_notification(self, notification_type: str, locale: Optional[str] = None, **kwargs) -> Dict[str, str]:
        """Get localized notification with title and message"""
        title = self.translate(f"notification.titles.{notification_type}", locale, **kwargs)
        message = self.translate(f"notification.messages.{notification_type}", locale, **kwargs)
        
        return {
            "title": title,
            "message": message
        }
    
    def get_validation_message(self, validation_type: str, locale: Optional[str] = None, **kwargs) -> str:
        """Get localized validation message"""
        return self.translate(f"validation.{validation_type}", locale, **kwargs)


# Global instance
localization = LocalizationService()