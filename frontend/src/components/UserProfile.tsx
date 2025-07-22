import React, { useState } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Avatar, 
  Typography, 
  Space, 
  Divider, 
  Row, 
  Col,
  Tabs,
  message,
  Modal,
  Upload
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  PhoneOutlined,
  LockOutlined,
  EditOutlined,
  SaveOutlined,
  CameraOutlined
} from '@ant-design/icons';
import type { UploadFile, RcFile } from 'antd/es/upload';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { authService } from '../services/auth.service';
import api from '../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface ProfileForm {
  full_name: string;
  email: string;
  phone: string;
}

interface PasswordForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

const UserProfile: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [profileForm] = Form.useForm<ProfileForm>();
  const [passwordForm] = Form.useForm<PasswordForm>();
  const [previewImage, setPreviewImage] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const handleProfileSubmit = async (values: ProfileForm) => {
    setLoading(true);
    try {
      await api.patch('/users/me', values);
      message.success('個人資料更新成功');
      setEditMode(false);
      // Note: You may want to refresh the user context here
    } catch (error) {
      message.error('更新失敗，請稍後再試');
    }
    setLoading(false);
  };

  const handlePasswordChange = async (values: PasswordForm) => {
    setPasswordLoading(true);
    try {
      await authService.changePassword(values.current_password, values.new_password);
      message.success('密碼更新成功');
      passwordForm.resetFields();
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || '密碼更新失敗';
      message.error(errorMessage);
    }
    setPasswordLoading(false);
  };

  const beforeUpload = (file: RcFile) => {
    const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png';
    if (!isJpgOrPng) {
      message.error('只能上傳 JPG/PNG 格式的圖片！');
    }
    const isLt2M = file.size / 1024 / 1024 < 2;
    if (!isLt2M) {
      message.error('圖片大小不能超過 2MB！');
    }
    return isJpgOrPng && isLt2M;
  };

  const handlePreview = async (file: UploadFile) => {
    if (!file.url && !file.preview) {
      file.preview = await getBase64(file.originFileObj as RcFile);
    }
    setPreviewImage(file.url || (file.preview as string));
    setPreviewOpen(true);
  };

  const getBase64 = (file: RcFile): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24 }}>
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Space direction="vertical" size="large">
            <Avatar 
              size={120} 
              icon={<UserOutlined />}
              src={user?.avatar_url}
            />
            <Upload
              listType="picture-card"
              fileList={fileList}
              onPreview={handlePreview}
              onChange={({ fileList: newFileList }) => setFileList(newFileList)}
              beforeUpload={beforeUpload}
              maxCount={1}
              showUploadList={false}
            >
              <Button icon={<CameraOutlined />} size="small">更換頭像</Button>
            </Upload>
            <div>
              <Title level={3}>{user?.full_name || user?.username}</Title>
              <Text type="secondary">{getRoleDisplayName(user?.role)}</Text>
            </div>
          </Space>
        </div>

        <Tabs defaultActiveKey="profile">
          <TabPane tab="個人資料" key="profile">
            <Form
              form={profileForm}
              layout="vertical"
              initialValues={{
                full_name: user?.full_name || '',
                email: user?.email || '',
                phone: user?.phone || '',
              }}
              onFinish={handleProfileSubmit}
              disabled={!editMode}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="姓名"
                    name="full_name"
                    rules={[{ required: true, message: '請輸入姓名' }]}
                  >
                    <Input prefix={<UserOutlined />} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="電子郵件"
                    name="email"
                    rules={[
                      { required: true, message: '請輸入電子郵件' },
                      { type: 'email', message: '請輸入有效的電子郵件' }
                    ]}
                  >
                    <Input prefix={<MailOutlined />} />
                  </Form.Item>
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="電話"
                    name="phone"
                    rules={[
                      { required: true, message: '請輸入電話號碼' },
                      { pattern: /^09\d{8}$|^0[2-8]\d{7,8}$/, message: '請輸入有效的台灣電話號碼' }
                    ]}
                  >
                    <Input prefix={<PhoneOutlined />} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="帳號">
                    <Input value={user?.username} disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              <Form.Item>
                {editMode ? (
                  <Space>
                    <Button 
                      type="primary" 
                      icon={<SaveOutlined />} 
                      htmlType="submit"
                      loading={loading}
                    >
                      儲存變更
                    </Button>
                    <Button onClick={() => {
                      setEditMode(false);
                      profileForm.resetFields();
                    }}>
                      取消
                    </Button>
                  </Space>
                ) : (
                  <Button 
                    type="primary" 
                    icon={<EditOutlined />} 
                    onClick={() => setEditMode(true)}
                  >
                    編輯資料
                  </Button>
                )}
              </Form.Item>
            </Form>
          </TabPane>

          <TabPane tab="安全設定" key="security">
            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={handlePasswordChange}
              style={{ maxWidth: 400 }}
            >
              <Form.Item
                label="目前密碼"
                name="current_password"
                rules={[{ required: true, message: '請輸入目前密碼' }]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>

              <Form.Item
                label="新密碼"
                name="new_password"
                rules={[
                  { required: true, message: '請輸入新密碼' },
                  { min: 8, message: '密碼長度至少8個字元' },
                  {
                    pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                    message: '密碼必須包含大小寫字母、數字和特殊符號'
                  }
                ]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>

              <Form.Item
                label="確認新密碼"
                name="confirm_password"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: '請確認新密碼' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('兩次輸入的密碼不一致'));
                    },
                  }),
                ]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  loading={passwordLoading}
                >
                  更新密碼
                </Button>
              </Form.Item>
            </Form>

            <Divider />

            <div>
              <Title level={5}>登入記錄</Title>
              <Text type="secondary">
                上次登入時間：{user?.last_login ? new Date(user.last_login).toLocaleString('zh-TW') : '無記錄'}
              </Text>
            </div>
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        open={previewOpen}
        title="預覽圖片"
        footer={null}
        onCancel={() => setPreviewOpen(false)}
      >
        <img alt="preview" style={{ width: '100%' }} src={previewImage} />
      </Modal>
    </div>
  );
};

// Helper function to get role display name
const getRoleDisplayName = (role?: string): string => {
  const roleMap: { [key: string]: string } = {
    super_admin: '超級管理員',
    manager: '經理',
    office_staff: '辦公室人員',
    driver: '司機',
    customer: '客戶'
  };
  return roleMap[role || ''] || role || '未知';
};

export default UserProfile;