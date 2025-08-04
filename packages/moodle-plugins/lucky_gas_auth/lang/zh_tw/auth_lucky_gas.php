<?php
/**
 * Lucky Gas SSO Authentication Plugin - Traditional Chinese Language Pack
 *
 * @package    auth_lucky_gas
 * @copyright  2025 Lucky Gas Company
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

$string['pluginname'] = '幸福氣單一登入';
$string['auth_lucky_gasdescription'] = '此驗證方法允許使用者使用幸福氣系統帳號登入 Moodle。';

// Configuration strings
$string['auth_lucky_gas_api_url'] = 'Lucky Gas API 網址';
$string['auth_lucky_gas_api_url_desc'] = '幸福氣 API 伺服器的基本網址';
$string['auth_lucky_gas_lucky_gas_url'] = 'Lucky Gas 系統網址';
$string['auth_lucky_gas_lucky_gas_url_desc'] = '幸福氣主系統的網址';
$string['auth_lucky_gas_client_id'] = '客戶端 ID';
$string['auth_lucky_gas_client_id_desc'] = 'Moodle 在幸福氣系統中的客戶端 ID';
$string['auth_lucky_gas_client_secret'] = '客戶端密鑰';
$string['auth_lucky_gas_client_secret_desc'] = 'Moodle 在幸福氣系統中的客戶端密鑰';

// Error messages
$string['auth_lucky_gas_login_failed'] = '登入失敗：無法連接到幸福氣驗證系統';
$string['auth_lucky_gas_invalid_credentials'] = '無效的使用者名稱或密碼';
$string['auth_lucky_gas_account_disabled'] = '您的帳號已被停用，請聯絡系統管理員';

// Settings page
$string['auth_lucky_gas_settings'] = '幸福氣單一登入設定';
$string['auth_lucky_gas_test_connection'] = '測試連線';
$string['auth_lucky_gas_test_success'] = '成功連接到幸福氣 API';
$string['auth_lucky_gas_test_failed'] = '無法連接到幸福氣 API，請檢查設定';