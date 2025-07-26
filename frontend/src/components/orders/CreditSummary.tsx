import React, { useEffect, useState } from 'react';
import { Card, Statistic, Alert, Spin, Row, Col, Tag } from 'antd';
import { DollarOutlined, WarningOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

interface CreditSummaryProps {
  customerId: number | null;
}

interface CreditInfo {
  customer_id: number;
  customer_name: string;
  credit_limit: number;
  current_balance: number;
  available_credit: number;
  overdue_amount: number;
  is_credit_blocked: boolean;
  credit_utilization: number;
}

const CreditSummary: React.FC<CreditSummaryProps> = ({ customerId }) => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [creditInfo, setCreditInfo] = useState<CreditInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (customerId) {
      fetchCreditInfo();
    } else {
      setCreditInfo(null);
      setError(null);
    }
  }, [customerId]);

  const fetchCreditInfo = async () => {
    if (!customerId) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/orders/credit/${customerId}`);
      setCreditInfo(response.data);
    } catch (err: any) {
      console.error('Failed to fetch credit info:', err);
      setError(t('orders.creditFetchError'));
    } finally {
      setLoading(false);
    }
  };

  if (!customerId) {
    return null;
  }

  if (loading) {
    return (
      <Card style={{ marginBottom: 16 }}>
        <Spin spinning={loading}>
          <div style={{ height: 100 }} />
        </Spin>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert
        message={t('orders.creditError')}
        description={error}
        type="error"
        showIcon
        style={{ marginBottom: 16 }}
      />
    );
  }

  if (!creditInfo) {
    return null;
  }

  const isWarning = creditInfo.credit_utilization > 80 || creditInfo.overdue_amount > 0;
  const isDanger = creditInfo.is_credit_blocked || creditInfo.available_credit <= 0;

  return (
    <Card 
      title={
        <span>
          <DollarOutlined /> {t('orders.creditSummary')}
          {creditInfo.is_credit_blocked && (
            <Tag color="red" style={{ marginLeft: 8 }}>
              {t('orders.creditBlocked')}
            </Tag>
          )}
        </span>
      }
      style={{ marginBottom: 16 }}
      bordered={false}
    >
      <Row gutter={16}>
        <Col span={6}>
          <Statistic
            title={t('orders.creditLimit')}
            value={creditInfo.credit_limit}
            prefix="NT$"
            precision={0}
            valueStyle={{ fontSize: 20 }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('orders.currentBalance')}
            value={creditInfo.current_balance}
            prefix="NT$"
            precision={0}
            valueStyle={{ fontSize: 20, color: creditInfo.current_balance > 0 ? '#ff4d4f' : '#52c41a' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('orders.availableCredit')}
            value={creditInfo.available_credit}
            prefix="NT$"
            precision={0}
            valueStyle={{ 
              fontSize: 20, 
              color: creditInfo.available_credit > 0 ? '#52c41a' : '#ff4d4f' 
            }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('orders.creditUtilization')}
            value={creditInfo.credit_utilization}
            suffix="%"
            precision={1}
            valueStyle={{ 
              fontSize: 20,
              color: creditInfo.credit_utilization > 80 ? '#ff4d4f' : 
                     creditInfo.credit_utilization > 50 ? '#faad14' : '#52c41a'
            }}
          />
        </Col>
      </Row>
      
      {creditInfo.overdue_amount > 0 && (
        <Alert
          message={t('orders.overdueWarning')}
          description={`${t('orders.overdueAmount')}: NT$${creditInfo.overdue_amount.toLocaleString()}`}
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginTop: 16 }}
        />
      )}
      
      {creditInfo.is_credit_blocked && (
        <Alert
          message={t('orders.creditBlockedWarning')}
          description={t('orders.creditBlockedDescription')}
          type="error"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}
    </Card>
  );
};

export default CreditSummary;