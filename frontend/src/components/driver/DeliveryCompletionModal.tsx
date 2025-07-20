import React, { useState, useRef } from 'react';
import { Modal, Form, Input, Upload, Button, Space, message, Image } from 'antd';
import { CameraOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import SignatureCanvas from 'react-signature-canvas';
import type { UploadFile } from 'antd/es/upload/interface';
import type { RouteStop } from '../../services/route.service';

const { TextArea } = Input;

interface DeliveryCompletionModalProps {
  visible: boolean;
  stop: RouteStop & { customerName?: string };
  onComplete: (data: {
    signature?: string;
    photo?: string;
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
  const [photoFile, setPhotoFile] = useState<UploadFile | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
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

  // Handle photo upload
  const handlePhotoUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setPhotoPreview(result);
      setPhotoFile({
        uid: '-1',
        name: file.name,
        status: 'done',
        url: result,
      } as UploadFile);
    };
    reader.readAsDataURL(file);
    return false; // Prevent auto upload
  };

  // Remove photo
  const removePhoto = () => {
    setPhotoFile(null);
    setPhotoPreview(null);
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
        photo: photoPreview || undefined,
        notes: values.notes,
      });
      
      // Reset form
      form.resetFields();
      clearSignature();
      removePhoto();
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
    removePhoto();
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

        {/* Delivery photo */}
        <Form.Item label="配送照片（選填）">
          {!photoFile ? (
            <Upload
              accept="image/*"
              beforeUpload={handlePhotoUpload}
              showUploadList={false}
            >
              <Button icon={<CameraOutlined />}>
                拍照或選擇照片
              </Button>
            </Upload>
          ) : (
            <div>
              <Image
                src={photoPreview!}
                alt="Delivery photo"
                style={{ maxWidth: '100%', maxHeight: 300 }}
              />
              <div style={{ marginTop: 8 }}>
                <Button
                  icon={<DeleteOutlined />}
                  onClick={removePhoto}
                  danger
                >
                  移除照片
                </Button>
              </div>
            </div>
          )}
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