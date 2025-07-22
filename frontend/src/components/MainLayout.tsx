import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Space, Typography, Drawer, Grid } from 'antd';
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
  CloseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import ProtectedRoute from './ProtectedRoute';
import NotificationBell from './common/NotificationBell';
import OfflineIndicator from './common/OfflineIndicator';
import { useOfflineSync } from '../hooks/useOfflineSync';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

const MainLayout: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);
  const { isOnline, syncPending, syncing } = useOfflineSync();
  const screens = useBreakpoint();

  // Menu items based on user role
  const getMenuItems = () => {
    const baseItems = [
      {
        key: '/dashboard',
        icon: <DashboardOutlined />,
        label: <span data-testid="menu-dashboard">{t('navigation.dashboard')}</span>,
      },
    ];

    if (user?.role === 'driver') {
      return [
        {
          key: '/driver',
          icon: <CarOutlined />,
          label: t('driver.todayDeliveries'),
        },
      ];
    }

    if (user?.role === 'customer') {
      return [
        {
          key: '/customer',
          icon: <UserOutlined />,
          label: t('customer.myOrders'),
        },
      ];
    }

    // Office staff, manager, and admin roles
    const officeItems = [
      {
        key: '/customers',
        icon: <UserOutlined />,
        label: <span data-testid="menu-customers">{t('navigation.customers')}</span>,
      },
      {
        key: '/orders',
        icon: <ShoppingCartOutlined />,
        label: <span data-testid="menu-orders">{t('navigation.orders')}</span>,
      },
      {
        key: '/routes',
        icon: <EnvironmentOutlined />,
        label: <span data-testid="menu-routes">{t('navigation.routes')}</span>,
      },
      {
        key: '/delivery-history',
        icon: <HistoryOutlined />,
        label: <span data-testid="menu-deliveries">{t('delivery.history')}</span>,
      },
    ];

    return [...baseItems, ...officeItems];
  };

  const menuItems = getMenuItems();

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: <span data-testid="profile-button">個人資料</span>,
      onClick: () => navigate('/profile'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: <span data-testid="logout-button">{t('app.logout')}</span>,
      onClick: logout,
    },
  ];

  const userMenu = <Menu items={userMenuItems} />;

  // Determine if we should show mobile layout
  // Use window width for reliable mobile detection
  const [windowWidth, setWindowWidth] = useState(() => {
    // Get initial width from window or document
    if (typeof window !== 'undefined') {
      return window.innerWidth || document.documentElement.clientWidth || 1024;
    }
    return 1024;
  });
  
  useEffect(() => {
    // Set initial width on mount in case SSR
    setWindowWidth(window.innerWidth || document.documentElement.clientWidth);
    
    const handleResize = () => {
      setWindowWidth(window.innerWidth || document.documentElement.clientWidth);
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // Consider mobile if width is less than 768px (standard tablet breakpoint)
  const isMobile = windowWidth < 768;

  // Handle menu item click
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
    if (isMobile) {
      setMobileMenuVisible(false);
    }
  };

  // Mobile menu drawer
  const mobileMenu = (
    <Drawer
      title={t('navigation.menu')}
      placement="left"
      onClose={() => setMobileMenuVisible(false)}
      open={mobileMenuVisible}
      bodyStyle={{ padding: 0 }}
      headerStyle={{ borderBottom: '1px solid #f0f0f0' }}
      width={280}
      data-testid="mobile-nav-menu"
    >
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={[
          ...menuItems,
          {
            key: 'divider-1',
            type: 'divider',
          },
          {
            key: 'profile',
            icon: <UserOutlined />,
            label: <span data-testid="mobile-profile-btn">個人資料</span>,
            onClick: () => {
              navigate('/profile');
              setMobileMenuVisible(false);
            },
          },
          {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: <span data-testid="logout-btn">{t('app.logout')}</span>,
            onClick: () => {
              logout();
              setMobileMenuVisible(false);
            },
          },
        ]}
        onClick={handleMenuClick}
      />
    </Drawer>
  );

  return (
    <ProtectedRoute>
      <Layout className="main-layout">
        {!isMobile && (
          <Sider trigger={null} collapsible collapsed={collapsed} data-testid="desktop-nav">
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
              onClick={handleMenuClick}
            />
          </Sider>
        )}
        <Layout>
          <Header style={{ 
            padding: 0, 
            background: '#fff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingRight: 24
          }}>
            {isMobile ? (
              <MenuFoldOutlined
                onClick={() => setMobileMenuVisible(true)}
                style={{ fontSize: 18, padding: '0 24px', cursor: 'pointer' }}
                data-testid="mobile-menu-trigger"
              />
            ) : (
              React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
                className: 'trigger',
                onClick: () => setCollapsed(!collapsed),
                style: { fontSize: 18, padding: '0 24px', cursor: 'pointer' }
              })
            )}
            <Space size={isMobile ? 'small' : 'large'}>
              <OfflineIndicator isOnline={isOnline} pendingSync={syncPending} syncing={syncing} />
              {!isMobile && <NotificationBell />}
              {!isMobile ? (
                <Dropdown overlay={userMenu} trigger={['click']}>
                  <Space style={{ cursor: 'pointer' }} data-testid="user-menu-trigger">
                    <Avatar icon={<UserOutlined />} />
                    <Text>{user?.full_name || user?.username}</Text>
                  </Space>
                </Dropdown>
              ) : (
                <Avatar icon={<UserOutlined />} />
              )}
            </Space>
          </Header>
          <Content className="site-layout-content">
            <Outlet />
          </Content>
        </Layout>
        {isMobile && mobileMenu}
      </Layout>
    </ProtectedRoute>
  );
};

export default MainLayout;