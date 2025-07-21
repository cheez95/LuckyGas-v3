import React, { useState, useRef } from 'react';
import { Modal, Form, Input, Button, Space, message, Image } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import SignatureCanvas from 'react-signature-canvas';
import PhotoCapture from './PhotoCapture';
import type { RouteStop } from '../../services/route.service';

const { TextArea } = Input;

interface DeliveryCompletionModalProps {
  visible: boolean;
  stop: RouteStop & { customerName?: string };
  onComplete: (data: {
    signature?: string;
    photos?: string[];
    notes?: string;
  }) => void;
  onCancel: () => void;
}

const DeliveryCompletionModal: React.FC<DeliveryCompletionModalProps> = ({
  visible,
  stop,
  onComplete,
  onCancel,
}) => {
  const [form] = Form.useForm();
  const signatureRef = useRef<SignatureCanvas>(null);
  const [signatureData, setSignatureData] = useState<string | null>(null);
  const [photos, setPhotos] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Clear signature
  const clearSignature = () => {
    if (signatureRef.current) {
      signatureRef.current.clear();
      setSignatureData(null);
    }
  };

  // Save signature
  const saveSignature = () => {
    if (signatureRef.current && !signatureRef.current.isEmpty()) {
      const data = signatureRef.current.toDataURL();
      setSignatureData(data);
      message.success('簽名已儲存');
    } else {
      message.warning('請先簽名');
    }
  };

  // Handle photos update
  const handlePhotosUpdate = (updatedPhotos: string[]) => {
    setPhotos(updatedPhotos);
  };

  // Handle form submission
  const handleSubmit = async (values: any) => {
    if (!signatureData) {
      message.warning('請提供客戶簽名');
      return;
    }

    setSubmitting(true);
    try {
      await onComplete({
        signature: signatureData,
        photos: photos.length > 0 ? photos : undefined,
        notes: values.notes,
      });
      
      // Reset form
      form.resetFields();
      clearSignature();
      setPhotos([]);
    } catch (error) {
      message.error('提交失敗，請重試');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle modal close
  const handleCancel = () => {
    form.resetFields();
    clearSignature();
    setPhotos([]);
    onCancel();
  };

  return (
    <Modal
      title={`完成配送 - ${stop.customerName || `訂單 #${stop.order_id}`}`}
      open={visible}
      onCancel={handleCancel}
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          取消
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={submitting}
          onClick={() => form.submit()}
        >
          確認完成
        </Button>,
      ]}
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {/* Customer signature */}
        <Form.Item label="客戶簽名" required>
          <div style={{
            border: '1px solid #d9d9d9',
            borderRadius: 8,
            padding: 8,
            backgroundColor: '#fafafa',
          }}>
            {!signatureData ? (
              <>
                <SignatureCanvas
                  ref={signatureRef}
                  canvasProps={{
                    width: 550,
                    height: 200,
                    style: {
                      border: '1px dashed #d9d9d9',
                      borderRadius: 4,
                      backgroundColor: '#fff',
                    },
                  }}
                />
                <Space style={{ marginTop: 8 }}>
                  <Button
                    icon={<EditOutlined />}
                    onClick={saveSignature}
                    type="primary"
                  >
                    儲存簽名
                  </Button>
                  <Button
                    icon={<DeleteOutlined />}
                    onClick={clearSignature}
                  >
                    清除
                  </Button>
                </Space>
              </>
            ) : (
              <div>
                <Image
                  src={signatureData}
                  alt="Customer signature"
                  style={{ maxWidth: '100%' }}
                />
                <Button
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    clearSignature();
                    setSignatureData(null);
                  }}
                  style={{ marginTop: 8 }}
                  danger
                >
                  重新簽名
                </Button>
              </div>
            )}
          </div>
        </Form.Item>

        {/* Delivery photos */}
        <Form.Item label="配送照片（選填）">
          <PhotoCapture
            onCapture={handlePhotosUpdate}
            maxPhotos={3}
            maxSizeMB={1}
          />
        </Form.Item>

        {/* Delivery notes */}
        <Form.Item
          label="配送備註（選填）"
          name="notes"
        >
          <TextArea
            rows={3}
            placeholder="輸入配送備註..."
            maxLength={500}
            showCount
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default DeliveryCompletionModal;