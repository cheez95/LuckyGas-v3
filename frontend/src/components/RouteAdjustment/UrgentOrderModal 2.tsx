import React, { useState } from 'react';
import {
  Modal,
  Button,
  Select,
  Typography,
  Alert,
  Spin,
} from 'antd';
import { TruckOutlined, WarningOutlined } from '@ant-design/icons';
import axios from 'axios';

interface UrgentOrderModalProps {
  open: boolean;
  onClose: () => void;
  orderId: string;
  routes: Array<{
    id: string;
    driverName: string;
    currentLoad: number;
    capacity: number;
    estimatedDelay: number;
  }>;
  onSuccess: () => void;
}

const { Title, Text } = Typography;
const { Option } = Select;

const UrgentOrderModal: React.FC<UrgentOrderModalProps> = ({
  open,
  onClose,
  orderId,
  routes,
  onSuccess,
}) => {
  const [selectedRoute, setSelectedRoute] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!selectedRoute) {
      setError('請選擇要插入的路線');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      await axios.post(`/api/v1/routes/${selectedRoute}/adjust/urgent-order`, {
        order_id: orderId,
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || '新增緊急訂單失敗');
    } finally {
      setLoading(false);
    }
  };

  const getLoadPercentage = (currentLoad: number, capacity: number) => {
    return Math.round((currentLoad / capacity) * 100);
  };

  const getLoadColor = (percentage: number) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 70) return 'warning';
    return 'success';
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <WarningOutlined style={{ color: '#faad14' }} />
          <span>插入緊急訂單</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="cancel" onClick={onClose} disabled={loading}>
          取消
        </Button>,
        <Button
          key="submit"
          type="primary"
          danger
          onClick={handleSubmit}
          disabled={loading || !selectedRoute}
          icon={loading ? <Spin size="small" /> : undefined}
        >
          {loading ? '處理中...' : '確認插入'}
        </Button>,
      ]}
    >
      <div style={{ marginBottom: 16 }}>
        <Alert
          type="warning"
          message={`訂單編號 ${orderId} 需要緊急配送，請選擇最適合的路線插入。`}
          showIcon
        />
      </div>

      {error && (
        <Alert
          type="error"
          message={error}
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      <div style={{ marginBottom: 24 }}>
        <Text strong style={{ marginBottom: 8, display: 'block' }}>選擇路線</Text>
        <Select
          value={selectedRoute}
          onChange={setSelectedRoute}
          placeholder="請選擇要插入的路線"
          style={{ width: '100%' }}
        >
          {routes.map((route) => {
            const loadPercentage = getLoadPercentage(route.currentLoad, route.capacity);
            return (
              <Option key={route.id} value={route.id}>
                <div style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text strong>
                      {route.driverName}
                    </Text>
                    <Text
                      type={getLoadColor(loadPercentage) === 'error' ? 'danger' : 
                            getLoadColor(loadPercentage) === 'warning' ? 'warning' : 'success'}
                      style={{ fontSize: 12 }}
                    >
                      載量 {loadPercentage}%
                    </Text>
                  </div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    預估延遲：{route.estimatedDelay} 分鐘
                  </Text>
                </div>
              </Option>
            );
          })}
        </Select>
      </div>

      {selectedRoute && (
        <div style={{ padding: 16, backgroundColor: '#e6f7ff', borderRadius: 4 }}>
          <Text style={{ color: '#1890ff' }}>
            <TruckOutlined style={{ marginRight: 8 }} />
            系統將自動尋找最佳插入點，以最小化對現有路線的影響。
          </Text>
        </div>
      )}
    </Modal>
  );
};

export default UrgentOrderModal;