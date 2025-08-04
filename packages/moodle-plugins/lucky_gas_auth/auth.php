<?php
/**
 * Lucky Gas SSO Authentication Plugin
 *
 * @package    auth_lucky_gas
 * @copyright  2025 Lucky Gas Company
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

require_once($CFG->libdir.'/authlib.php');

/**
 * Lucky Gas SSO authentication plugin.
 */
class auth_plugin_lucky_gas extends auth_plugin_base {

    /**
     * Constructor.
     */
    public function __construct() {
        $this->authtype = 'lucky_gas';
        $this->config = get_config('auth_lucky_gas');
    }

    /**
     * Returns true if the username and password work and false if they are
     * wrong or don't exist.
     *
     * @param string $username The username
     * @param string $password The password
     * @return bool Authentication success or failure.
     */
    public function user_login($username, $password) {
        global $CFG, $DB;
        
        // Validate against Lucky Gas API
        $api_url = $this->config->api_url . '/auth/validate';
        
        $postdata = http_build_query([
            'username' => $username,
            'password' => $password,
            'client_id' => $this->config->client_id,
            'client_secret' => $this->config->client_secret
        ]);
        
        $opts = [
            'http' => [
                'method'  => 'POST',
                'header'  => 'Content-Type: application/x-www-form-urlencoded',
                'content' => $postdata
            ]
        ];
        
        $context = stream_context_create($opts);
        $result = file_get_contents($api_url, false, $context);
        
        if ($result === FALSE) {
            return false;
        }
        
        $response = json_decode($result, true);
        
        if ($response['success'] === true) {
            // Update user info from Lucky Gas system
            $this->update_user_info($username, $response['user']);
            return true;
        }
        
        return false;
    }

    /**
     * Updates the user's password.
     *
     * @param  object  $user        User table object
     * @param  string  $newpassword Plaintext password
     * @return boolean result
     */
    public function user_update_password($user, $newpassword) {
        // Password updates should be done through Lucky Gas system
        return false;
    }

    /**
     * Returns true if this authentication plugin can change the user's password.
     *
     * @return bool
     */
    public function can_change_password() {
        return false;
    }

    /**
     * Returns the URL for changing the user's password, or empty if the default can be used.
     *
     * @return moodle_url
     */
    public function change_password_url() {
        return new moodle_url($this->config->lucky_gas_url . '/profile/change-password');
    }

    /**
     * Returns true if plugin allows resetting of internal password.
     *
     * @return bool
     */
    public function can_reset_password() {
        return false;
    }

    /**
     * Returns true if plugin can be manually set.
     *
     * @return bool
     */
    public function can_be_manually_set() {
        return false;
    }

    /**
     * Prints a form for configuring this authentication plugin.
     *
     * @param array $config An object containing all the data for this page.
     * @param array $err string.
     * @param array $user_fields
     * @return string
     */
    public function config_form($config, $err, $user_fields) {
        include 'config.html';
    }

    /**
     * Processes and stores configuration data for this authentication plugin.
     *
     * @param stdClass $config
     * @return bool
     */
    public function process_config($config) {
        // Set to defaults if undefined
        if (!isset($config->api_url)) {
            $config->api_url = 'https://api.luckygas.com.tw/v1';
        }
        if (!isset($config->lucky_gas_url)) {
            $config->lucky_gas_url = 'https://www.luckygas.com.tw';
        }
        if (!isset($config->client_id)) {
            $config->client_id = '';
        }
        if (!isset($config->client_secret)) {
            $config->client_secret = '';
        }

        // Save settings
        set_config('api_url', $config->api_url, 'auth_lucky_gas');
        set_config('lucky_gas_url', $config->lucky_gas_url, 'auth_lucky_gas');
        set_config('client_id', $config->client_id, 'auth_lucky_gas');
        set_config('client_secret', $config->client_secret, 'auth_lucky_gas');
        
        return true;
    }

    /**
     * Update user information from Lucky Gas system
     *
     * @param string $username
     * @param array $userinfo
     */
    private function update_user_info($username, $userinfo) {
        global $DB, $CFG;
        
        $user = $DB->get_record('user', ['username' => $username]);
        
        if ($user) {
            $user->firstname = $userinfo['firstname'];
            $user->lastname = $userinfo['lastname'];
            $user->email = $userinfo['email'];
            $user->department = $userinfo['department'];
            $user->lang = 'zh_tw'; // Traditional Chinese
            
            $DB->update_record('user', $user);
            
            // Update role based on Lucky Gas role
            $this->sync_user_role($user->id, $userinfo['role']);
        }
    }

    /**
     * Sync user role from Lucky Gas to Moodle
     *
     * @param int $userid
     * @param string $lucky_gas_role
     */
    private function sync_user_role($userid, $lucky_gas_role) {
        global $DB;
        
        $context = context_system::instance();
        
        // Map Lucky Gas roles to Moodle roles
        $role_mapping = [
            'admin' => 'manager',
            'manager' => 'teacher',
            'office_staff' => 'student',
            'driver' => 'student'
        ];
        
        if (isset($role_mapping[$lucky_gas_role])) {
            $roleid = $DB->get_field('role', 'id', ['shortname' => $role_mapping[$lucky_gas_role]]);
            
            if ($roleid) {
                // Remove other roles first
                role_unassign_all(['userid' => $userid, 'contextid' => $context->id]);
                
                // Assign new role
                role_assign($roleid, $userid, $context->id);
            }
        }
    }

    /**
     * Hook for overriding behaviour of login page.
     * This method is called from login/index.php page for all enabled auth plugins.
     */
    public function loginpage_hook() {
        global $CFG, $SESSION;
        
        // Check if we have SSO token
        $token = optional_param('sso_token', '', PARAM_TEXT);
        
        if (!empty($token)) {
            // Validate token with Lucky Gas API
            $api_url = $this->config->api_url . '/auth/validate-token';
            
            $opts = [
                'http' => [
                    'method'  => 'GET',
                    'header'  => "Authorization: Bearer $token\r\n"
                ]
            ];
            
            $context = stream_context_create($opts);
            $result = file_get_contents($api_url, false, $context);
            
            if ($result !== FALSE) {
                $response = json_decode($result, true);
                
                if ($response['success'] === true) {
                    // Create or update user
                    $user = $this->create_user_from_sso($response['user']);
                    
                    if ($user) {
                        // Complete login
                        complete_user_login($user);
                        
                        // Redirect to dashboard
                        redirect($CFG->wwwroot . '/my/');
                    }
                }
            }
        }
    }

    /**
     * Create or update user from SSO data
     *
     * @param array $userdata
     * @return stdClass|false
     */
    private function create_user_from_sso($userdata) {
        global $DB, $CFG;
        
        $user = $DB->get_record('user', ['username' => $userdata['username']]);
        
        if (!$user) {
            // Create new user
            $user = new stdClass();
            $user->auth = 'lucky_gas';
            $user->confirmed = 1;
            $user->username = $userdata['username'];
            $user->password = AUTH_PASSWORD_NOT_CACHED;
            $user->firstname = $userdata['firstname'];
            $user->lastname = $userdata['lastname'];
            $user->email = $userdata['email'];
            $user->department = $userdata['department'];
            $user->lang = 'zh_tw';
            $user->timecreated = time();
            $user->timemodified = time();
            
            $user->id = $DB->insert_record('user', $user);
            
            // Trigger event
            \core\event\user_created::create_from_userid($user->id)->trigger();
        } else {
            // Update existing user
            $user->firstname = $userdata['firstname'];
            $user->lastname = $userdata['lastname'];
            $user->email = $userdata['email'];
            $user->department = $userdata['department'];
            $user->timemodified = time();
            
            $DB->update_record('user', $user);
        }
        
        // Sync role
        $this->sync_user_role($user->id, $userdata['role']);
        
        return $user;
    }
}