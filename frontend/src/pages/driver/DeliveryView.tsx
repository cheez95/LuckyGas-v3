import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, Tag, Descriptions, Modal, Input, Select, message, Spin } from 'antd';
import {
  ArrowLeftOutlined,
  PhoneOutlined,
  MessageOutlined,
  CheckCircleOutlined,
  CameraOutlined,
  EditOutlined,
  WarningOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import SignatureCapture from './components/SignatureCapture';
import PhotoCapture from './components/PhotoCapture';
import './DeliveryView.css';

const { TextArea } = Input;
const { Option } = Select;

interface DeliveryData {
  id: string;
  orderId: string;
  customer: {
    id: string;
    name: string;
    phone: string;
    address: string;
    notes?: string;
  };
  products: Array<{
    name: string;
    quantity: number;
    type: string;
    serialNumber?: string;
  }>;
  status: string;
  specialInstructions?: string;
}

const DeliveryView: React.FC = () => {
  const { routeId, deliveryIndex } = useParams<{ routeId: string; deliveryIndex: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [delivery, setDelivery] = useState<DeliveryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [arrived, setArrived] = useState(false);
  const [completionModalVisible, setCompletionModalVisible] = useState(false);
  const [issueModalVisible, setIssueModalVisible] = useState(false);
  const [signature, setSignature] = useState<string | null>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const [deliveryNotes, setDeliveryNotes] = useState('');
  const [issueType, setIssueType] = useState('');
  const [issueNotes, setIssueNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchDeliveryDetails();
  }, [routeId, deliveryIndex]);

  const fetchDeliveryDetails = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/driver/routes/${routeId}/deliveries/${deliveryIndex}`);
      setDelivery(response.data);
    } catch (error) {
      const cached = localStorage.getItem(`delivery_${routeId}_${deliveryIndex}`);
      if (cached) {
        setDelivery(JSON.parse(cached));
      } else {
        message.error(t('driver.delivery.loadError'));
        navigate(`/driver/route/${routeId}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleArrived = async () => {
    try {
      await api.post(`/driver/deliveries/${delivery?.id}/arrived`);
      setArrived(true);
      message.success(t('driver.delivery.arrivedSuccess'));
    } catch (error) {
      // Queue for offline sync
      const offlineQueue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
      offlineQueue.push({
        type: 'arrived',
        deliveryId: delivery?.id,
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('offline_queue', JSON.stringify(offlineQueue));
      setArrived(true);
    }
  };

  const handleDelivered = () => {
    setCompletionModalVisible(true);
  };

  const handleReportIssue = () => {
    setIssueModalVisible(true);
  };

  const handleConfirmDelivery = async () => {
    if (!signature && !photo) {
      message.warning(t('driver.delivery.requireProof'));
      return;
    }

    setSubmitting(true);
    try {
      const data = {
        status: 'delivered',
        signature,
        photo,
        notes: deliveryNotes,
        completedAt: new Date().toISOString()
      };

      await api.post(`/driver/deliveries/${delivery?.id}/complete`, data);
      
      message.success(t('driver.delivery.completeSuccess'));
      setCompletionModalVisible(false);
      
      // Navigate to next delivery
      const nextIndex = parseInt(deliveryIndex || '0') + 1;
      navigate(`/driver/route/${routeId}`);
    } catch (error) {
      // Queue for offline sync
      const offlineQueue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
      offlineQueue.push({
        type: 'delivery_complete',
        deliveryId: delivery?.id,
        data: {
          status: 'delivered',
          signature,
          photo,
          notes: deliveryNotes,
          completedAt: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('offline_queue', JSON.stringify(offlineQueue));
      
      message.success(t('driver.delivery.queuedForSync'));
      setCompletionModalVisible(false);
      navigate(`/driver/route/${routeId}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitIssue = async () => {
    if (!issueType) {
      message.warning(t('driver.delivery.selectIssueType'));
      return;
    }

    setSubmitting(true);
    try {
      await api.post(`/driver/deliveries/${delivery?.id}/issue`, {
        type: issueType,
        notes: issueNotes,
        reportedAt: new Date().toISOString()
      });

      message.success(t('driver.delivery.issueReported'));
      setIssueModalVisible(false);
      navigate(`/driver/route/${routeId}`);
    } catch (error) {
      message.error(t('driver.delivery.issueError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCallCustomer = () => {
    window.location.href = `tel:${delivery?.customer.phone}`;
  };

  if (loading) {
    return (
      <div className="delivery-loading">
        <Spin size="large" />
      </div>
    );
  }

  if (!delivery) {
    return null;
  }

  return (
    <div className="delivery-view">
      {/* Header */}
      <div className="delivery-header">
        <Button
          icon={<ArrowLeftOutlined />}
          type="text"
          onClick={() => navigate(`/driver/route/${routeId}`)}
        />
        <h2 data-testid="current-delivery">
          {t('driver.delivery.title', { 
            current: parseInt(deliveryIndex || '0') + 1, 
            total: 5 // This should come from route data
          })}
        </h2>
        <div style={{ width: 40 }} />
      </div>

      {/* Customer Info Card */}
      <Card className="customer-card" data-testid="current-delivery">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div className="customer-header">
            <h3 data-testid="customer-name">{delivery.customer.name}</h3>
            <Space>
              <Button
                icon={<PhoneOutlined />}
                shape="circle"
                onClick={handleCallCustomer}
                data-testid="call-customer-button"
              />
              <Button
                icon={<MessageOutlined />}
                shape="circle"
                onClick={() => navigate(`/driver/sms/${delivery.customer.id}`)}
                data-testid="sms-customer-button"
              />
            </Space>
          </div>
          
          <div className="delivery-address" data-testid="delivery-address">
            <EnvironmentOutlined />
            <span>{delivery.customer.address}</span>
          </div>

          {delivery.customer.notes && (
            <div className="customer-notes">
              <WarningOutlined /> {delivery.customer.notes}
            </div>
          )}
        </Space>
      </Card>

      {/* Products Card */}
      <Card title={t('driver.delivery.products')} className="products-card" data-testid="delivery-products">
        {delivery.products.map((product, index) => (
          <div key={index} className="product-item">
            <Space>
              <Tag color="blue">{product.quantity}x</Tag>
              <span className="product-name">{product.type}</span>
              {product.serialNumber && (
                <span className="serial-number">SN: {product.serialNumber}</span>
              )}
            </Space>
          </div>
        ))}
      </Card>

      {/* Special Instructions */}
      {delivery.specialInstructions && (
        <Card className="instructions-card">
          <Space>
            <WarningOutlined style={{ color: '#faad14' }} />
            <span>{delivery.specialInstructions}</span>
          </Space>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="action-buttons">
        {!arrived ? (
          <Button
            type="primary"
            size="large"
            block
            onClick={handleArrived}
            data-testid="arrived-button"
          >
            {t('driver.delivery.arrived')}
          </Button>
        ) : (
          <>
            <Button
              type="primary"
              size="large"
              icon={<CheckCircleOutlined />}
              block
              onClick={handleDelivered}
              data-testid="delivered-button"
            >
              {t('driver.delivery.delivered')}
            </Button>
            <Button
              size="large"
              danger
              block
              onClick={handleReportIssue}
              data-testid="report-issue-button"
            >
              {t('driver.delivery.reportIssue')}
            </Button>
          </>
        )}
      </div>

      {/* Completion Modal */}
      <Modal
        title={t('driver.delivery.completeDelivery')}
        open={completionModalVisible}
        onCancel={() => setCompletionModalVisible(false)}
        footer={null}
        className="completion-modal"
        data-testid="delivery-completion-modal"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Signature Capture */}
          <div className="proof-section">
            <h4>{t('driver.delivery.signature')}</h4>
            <SignatureCapture
              onSignature={setSignature}
              signature={signature}
            />
          </div>

          {/* Photo Capture */}
          <div className="proof-section">
            <h4>{t('driver.delivery.photo')}</h4>
            <PhotoCapture
              onPhoto={setPhoto}
              photo={photo}
            />
          </div>

          {/* Delivery Notes */}
          <div>
            <h4>{t('driver.delivery.notes')}</h4>
            <TextArea
              rows={3}
              value={deliveryNotes}
              onChange={(e) => setDeliveryNotes(e.target.value)}
              placeholder={t('driver.delivery.notesPlaceholder')}
              data-testid="delivery-notes"
            />
          </div>

          {/* Confirm Button */}
          <Button
            type="primary"
            size="large"
            block
            onClick={handleConfirmDelivery}
            loading={submitting}
            data-testid="confirm-delivery-button"
          >
            {t('driver.delivery.confirm')}
          </Button>
          
          {!signature && !photo && (
            <Button
              type="link"
              block
              onClick={() => {
                setCompletionModalVisible(false);
                handleConfirmDelivery();
              }}
              data-testid="skip-signature-button"
            >
              {t('driver.delivery.skipProof')}
            </Button>
          )}
        </Space>
      </Modal>

      {/* Issue Modal */}
      <Modal
        title={t('driver.delivery.reportIssue')}
        open={issueModalVisible}
        onCancel={() => setIssueModalVisible(false)}
        footer={null}
        className="issue-modal"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <h4>{t('driver.delivery.issueType')}</h4>
            <Select
              style={{ width: '100%' }}
              placeholder={t('driver.delivery.selectIssueType')}
              value={issueType}
              onChange={setIssueType}
              size="large"
            >
              <Option value="absent" data-testid="issue-type-absent">
                {t('driver.delivery.issues.absent')}
              </Option>
              <Option value="rejected" data-testid="issue-type-rejected">
                {t('driver.delivery.issues.rejected')}
              </Option>
              <Option value="wrong_address">
                {t('driver.delivery.issues.wrongAddress')}
              </Option>
              <Option value="damaged">
                {t('driver.delivery.issues.damaged')}
              </Option>
              <Option value="other">
                {t('driver.delivery.issues.other')}
              </Option>
            </Select>
          </div>

          {issueType === 'rejected' && (
            <div>
              <h4>{t('driver.delivery.rejectionReason')}</h4>
              <Select
                style={{ width: '100%' }}
                placeholder={t('driver.delivery.selectReason')}
                size="large"
                data-testid="rejection-reason"
              >
                <Option value="wrong_product">{t('driver.delivery.reasons.wrongProduct')}</Option>
                <Option value="damaged">{t('driver.delivery.reasons.damaged')}</Option>
                <Option value="price_dispute">{t('driver.delivery.reasons.priceDispute')}</Option>
                <Option value="other">{t('driver.delivery.reasons.other')}</Option>
              </Select>
            </div>
          )}

          <div>
            <h4>{t('driver.delivery.issueNotes')}</h4>
            <TextArea
              rows={4}
              value={issueNotes}
              onChange={(e) => setIssueNotes(e.target.value)}
              placeholder={t('driver.delivery.issueNotesPlaceholder')}
              data-testid="issue-notes"
            />
          </div>

          <Button
            type="primary"
            size="large"
            block
            onClick={handleSubmitIssue}
            loading={submitting}
            data-testid="submit-issue-button"
          >
            {t('driver.delivery.submitIssue')}
          </Button>
        </Space>
      </Modal>
    </div>
  );
};

export default DeliveryView;