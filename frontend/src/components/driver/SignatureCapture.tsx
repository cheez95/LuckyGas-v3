import React, { useRef, useState, useEffect } from 'react';
import { Modal, Button, Space, message } from 'antd';
import { ClearOutlined, CheckOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

interface SignatureCaptureProps {
  visible: boolean;
  onConfirm: (signature: string) => void;
  onCancel: () => void;
  recipientName?: string;
}

const SignatureCapture: React.FC<SignatureCaptureProps> = ({
  visible,
  onConfirm,
  onCancel,
  recipientName
}) => {
  const { t } = useTranslation();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSignature, setHasSignature] = useState(false);

  useEffect(() => {
    if (visible && canvasRef.current) {
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      if (context) {
        // Set canvas size for mobile devices
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
        
        // Configure drawing style
        context.strokeStyle = '#000000';
        context.lineWidth = 2;
        context.lineCap = 'round';
        context.lineJoin = 'round';
      }
    }
  }, [visible]);

  const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    setIsDrawing(true);
    setHasSignature(true);
    
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    const rect = canvas.getBoundingClientRect();
    let x, y;

    if ('touches' in e) {
      x = e.touches[0].clientX - rect.left;
      y = e.touches[0].clientY - rect.top;
    } else {
      x = e.clientX - rect.left;
      y = e.clientY - rect.top;
    }

    context.beginPath();
    context.moveTo(x, y);
  };

  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (!isDrawing) return;

    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    const rect = canvas.getBoundingClientRect();
    let x, y;

    if ('touches' in e) {
      x = e.touches[0].clientX - rect.left;
      y = e.touches[0].clientY - rect.top;
    } else {
      x = e.clientX - rect.left;
      y = e.clientY - rect.top;
    }

    context.lineTo(x, y);
    context.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    context.clearRect(0, 0, canvas.width, canvas.height);
    setHasSignature(false);
  };

  const confirmSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas || !hasSignature) {
      message.warning(t('driver.signatureRequired'));
      return;
    }

    // Convert canvas to base64 string
    const signature = canvas.toDataURL('image/png');
    onConfirm(signature);
    clearSignature();
  };

  const handleCancel = () => {
    clearSignature();
    onCancel();
  };

  return (
    <Modal
      title={t('driver.deliverySignature')}
      open={visible}
      onCancel={handleCancel}
      width={window.innerWidth > 768 ? 600 : '95%'}
      footer={null}
      centered
      data-testid="signature-modal"
    >
      <div className="signature-capture-container">
        {recipientName && (
          <div style={{ marginBottom: 16, textAlign: 'center' }}>
            <strong>{t('driver.recipientName')}:</strong> {recipientName}
          </div>
        )}
        
        <div 
          style={{ 
            border: '2px solid #d9d9d9',
            borderRadius: 4,
            marginBottom: 16,
            position: 'relative',
            backgroundColor: '#fff',
            touchAction: 'none'
          }}
        >
          <canvas
            ref={canvasRef}
            data-testid="signature-canvas"
            style={{
              width: '100%',
              height: 200,
              cursor: 'crosshair',
              touchAction: 'none'
            }}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawing}
            onTouchMove={draw}
            onTouchEnd={stopDrawing}
          />
          
          {!hasSignature && (
            <div 
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                color: '#00000040',
                fontSize: 16,
                pointerEvents: 'none'
              }}
            >
              {t('driver.signHere')}
            </div>
          )}
        </div>

        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button
            icon={<ClearOutlined />}
            onClick={clearSignature}
            disabled={!hasSignature}
            data-testid="clear-signature-button"
          >
            {t('driver.clearSignature')}
          </Button>
          
          <Space>
            <Button onClick={handleCancel}>
              {t('common.cancel')}
            </Button>
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={confirmSignature}
              disabled={!hasSignature}
              data-testid="confirm-signature-button"
            >
              {t('driver.confirmDelivery')}
            </Button>
          </Space>
        </Space>
      </div>
    </Modal>
  );
};

export default SignatureCapture;