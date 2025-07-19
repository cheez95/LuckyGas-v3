import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Space, Typography } from 'antd';
import {
  DashboardOutlined,
  UserOutlined,
  ShoppingCartOutlined,
  EnvironmentOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  CarOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import ProtectedRoute from './ProtectedRoute';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  // Menu items based on user role
  const getMenuItems = () => {
    const baseItems = [
      {
        key: '/dashboard',
        icon: <DashboardOutlined />,
        label: '總覽',
      },
    ];

    if (user?.role === 'driver') {
      return [
        {
          key: '/driver',
          icon: <CarOutlined />,
          label: '配送任務',
        },
      ];
    }

    if (user?.role === 'customer') {
      return [
        {
          key: '/customer',
          icon: <UserOutlined />,
          label: '我的訂單',
        },
      ];
    }

    // Office staff, manager, and admin roles
    const officeItems = [
      {
        key: '/customers',
        icon: <UserOutlined />,
        label: '客戶管理',
      },
      {
        key: '/orders',
        icon: <ShoppingCartOutlined />,
        label: '訂單管理',
      },
      {
        key: '/routes',
        icon: <EnvironmentOutlined />,
        label: '路線管理',
      },
      {
        key: '/delivery-history',
        icon: <HistoryOutlined />,
        label: '配送歷史',
      },
    ];

    return [...baseItems, ...officeItems];
  };

  const menuItems = getMenuItems();

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '登出',
      onClick: logout,
    },
  ];

  const userMenu = <Menu items={userMenuItems} />;

  return (
    <ProtectedRoute>
      <Layout className="main-layout">
        <Sider trigger={null} collapsible collapsed={collapsed}>
          <div className="logo" style={{ 
            height: 64, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            color: '#fff',
            fontSize: collapsed ? 20 : 24,
            fontWeight: 'bold'
          }}>
            {collapsed ? 'LG' : 'Lucky Gas'}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
        <Layout>
          <Header style={{ 
            padding: 0, 
            background: '#fff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingRight: 24
          }}>
            {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
              className: 'trigger',
              onClick: () => setCollapsed(!collapsed),
              style: { fontSize: 18, padding: '0 24px', cursor: 'pointer' }
            })}
            <Dropdown overlay={userMenu} trigger={['click']}>
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <Text>{user?.full_name || user?.username}</Text>
              </Space>
            </Dropdown>
          </Header>
          <Content className="site-layout-content">
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </ProtectedRoute>
  );
};

export default MainLayout;