import React, { useState } from 'react';
import { Badge, Button, Drawer, List, Typography, Space, Empty, Tag } from 'antd';
import { BellOutlined, DeleteOutlined, ReadOutlined } from '@ant-design/icons';
import { useNotification } from '../../contexts/NotificationContext';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-tw';

dayjs.extend(relativeTime);
dayjs.locale('zh-tw');

const { Text, Title } = Typography;

const NotificationBell: React.FC = () => {
  const [drawerVisible, setDrawerVisible] = useState(false);
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearNotification,
    clearAll,
  } = useNotification();

  const getNotificationTypeColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const handleNotificationClick = (notificationId: string) => {
    markAsRead(notificationId);
  };

  return (
    <>
      <Badge count={unreadCount} offset={[-5, 5]}>
        <Button
          type="text"
          icon={<BellOutlined />}
          onClick={() => setDrawerVisible(true)}
          style={{ fontSize: '16px' }}
        />
      </Badge>

      <Drawer
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>通知中心</Title>
            <Space>
              {notifications.length > 0 && (
                <>
                  <Button
                    size="small"
                    icon={<ReadOutlined />}
                    onClick={markAllAsRead}
                    disabled={unreadCount === 0}
                  >
                    全部標記已讀
                  </Button>
                  <Button
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={clearAll}
                    danger
                  >
                    清除全部
                  </Button>
                </>
              )}
            </Space>
          </div>
        }
        placement="right"
        width={400}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        bodyStyle={{ padding: 0 }}
      >
        {notifications.length === 0 ? (
          <Empty
            description="暫無通知"
            style={{ marginTop: 50 }}
          />
        ) : (
          <List
            dataSource={notifications}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  backgroundColor: item.read ? 'transparent' : '#f0f2f5',
                  padding: '12px 16px',
                  borderBottom: '1px solid #f0f0f0',
                }}
                onClick={() => handleNotificationClick(item.id)}
                actions={[
                  <Button
                    key="delete"
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      clearNotification(item.id);
                    }}
                    danger
                  />,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong={!item.read}>{item.title}</Text>
                      <Tag color={getNotificationTypeColor(item.type)}>
                        {item.type === 'success' && '成功'}
                        {item.type === 'info' && '資訊'}
                        {item.type === 'warning' && '警告'}
                        {item.type === 'error' && '錯誤'}
                      </Tag>
                      {!item.read && (
                        <Badge
                          status="processing"
                          text=""
                          style={{ marginLeft: 8 }}
                        />
                      )}
                    </Space>
                  }
                  description={
                    <div>
                      <Text type="secondary">{item.message}</Text>
                      <div style={{ marginTop: 4 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {dayjs(item.timestamp).fromNow()}
                        </Text>
                      </div>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Drawer>
    </>
  );
};

export default NotificationBell;