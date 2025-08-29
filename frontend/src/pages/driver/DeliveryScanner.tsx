import React, { useState, useRef, useEffect } from 'react';
import { Card, Button, Space, Typography, Input, message, Modal, Form } from 'antd';
import {
  ArrowLeftOutlined,
  CameraOutlined,
  QrcodeOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import { BrowserMultiFormatReader, NotFoundException } from '@zxing/library';

const { Title, Text } = Typography;

const DeliveryScanner: React.FC = () => {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const codeReaderRef = useRef<BrowserMultiFormatReader | null>(null);
  const { sendMessage } = useWebSocketContext();
  const [scanning, setScanning] = useState(false);
  const [manualEntry, setManualEntry] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    // Initialize code reader
    codeReaderRef.current = new BrowserMultiFormatReader();
    
    if (scanning) {
      startCamera();
    } else {
      stopCamera();
    }

    return () => {
      stopCamera();
      // Clean up code reader
      if (codeReaderRef.current) {
        codeReaderRef.current.reset();
      }
    };
  }, [scanning]);

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { 
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false,
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        setStream(mediaStream);
        
        // Start continuous scanning
        startContinuousScanning();
      }
    } catch (error) {
      console.error('Camera error:', error);
      message.error('無法啟動相機，請確認已授權相機權限');
      setScanning(false);
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    stopContinuousScanning();
  };

  // Add continuous scanning functionality
  const continuousScanIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const startContinuousScanning = () => {
    // Scan every 500ms for better QR code detection
    continuousScanIntervalRef.current = window.setInterval(() => {
      if (scanning && videoRef.current && videoRef.current.readyState === 4) {
        captureAndScan();
      }
    }, 500);
  };
  
  const stopContinuousScanning = () => {
    if (continuousScanIntervalRef.current) {
      window.clearInterval(continuousScanIntervalRef.current);
      continuousScanIntervalRef.current = null;
    }
  };

  const captureAndScan = async () => {
    if (!videoRef.current || !canvasRef.current || !codeReaderRef.current) {
      console.error('Required references not available');
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    if (!context) {
      console.error('Could not get canvas context');
      return;
    }

    try {
      // Draw current video frame to canvas
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Create image data from canvas
      const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
      
      // Decode QR code from image data
      const result = await codeReaderRef.current.decodeFromImageElement(canvas);
      
      if (result) {
        // console.log('QR Code detected:', result.getText());
        handleQRCodeScanned(result.getText());
      } else {
        // No QR code found, show feedback to user
        message.info('未偵測到 QR Code，請對準後再試');
      }
    } catch (error) {
      if (error instanceof NotFoundException) {
        // No QR code found in image
        message.info('未偵測到 QR Code，請對準後再試');
      } else {
        console.error('QR scanning error:', error);
        message.error('掃描失敗，請再試一次');
      }
    }
  };

  const handleQRCodeScanned = (code: string) => {
    // Parse QR code (format: ORDER_ID-CUSTOMER_ID)
    const [orderId, customerId] = code.split('-').slice(0, 2);
    
    if (!orderId || !customerId) {
      message.error('無效的 QR Code');
      return;
    }

    // Send delivery confirmation
    sendMessage({
      type: 'delivery.confirmed',
      order_id: orderId,
      customer_id: customerId,
      confirmed_at: new Date().toISOString(),
      confirmation_type: 'qr_code',
    });

    message.success('配送確認成功');
    stopCamera();
    
    // Show success modal
    Modal.success({
      title: '配送完成',
      content: `訂單 ${orderId} 已確認送達`,
      onOk: () => navigate('/driver'),
    });
  };

  const handleManualConfirm = (values: { orderId: string; cylinderSerial: string }) => {
    // Send manual confirmation
    sendMessage({
      type: 'delivery.confirmed',
      order_id: values.orderId,
      cylinder_serial: values.cylinderSerial,
      confirmed_at: new Date().toISOString(),
      confirmation_type: 'manual',
    });

    message.success('配送確認成功');
    
    Modal.success({
      title: '配送完成',
      content: `訂單 ${values.orderId} 已確認送達`,
      onOk: () => navigate('/driver'),
    });
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#f0f2f5' }}>
      {/* Header */}
      <Card 
        size="small" 
        style={{ borderRadius: 0 }}
        bodyStyle={{ padding: '8px 16px' }}
      >
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/driver')}
          >
            返回
          </Button>
          <Title level={5} style={{ margin: 0 }}>掃描確認配送</Title>
          <div style={{ width: 32 }} />
        </Space>
      </Card>

      {/* Scanner Area */}
      <div style={{ flex: 1, padding: 16 }}>
        {!scanning && !manualEntry && (
          <Card style={{ textAlign: 'center', marginTop: 50 }}>
            <Space direction="vertical" size="large">
              <QrcodeOutlined style={{ fontSize: 64, color: '#1890ff' }} />
              <Title level={4}>掃描客戶 QR Code</Title>
              <Text type="secondary">
                請掃描客戶提供的 QR Code 以確認配送
              </Text>
              <Space>
                <Button 
                  type="primary" 
                  size="large"
                  icon={<CameraOutlined />}
                  onClick={() => setScanning(true)}
                >
                  開始掃描
                </Button>
                <Button 
                  size="large"
                  onClick={() => setManualEntry(true)}
                >
                  手動輸入
                </Button>
              </Space>
            </Space>
          </Card>
        )}

        {scanning && (
          <Card style={{ position: 'relative', overflow: 'hidden' }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              style={{ width: '100%', height: 'auto' }}
            />
            <canvas
              ref={canvasRef}
              style={{ display: 'none' }}
            />
            <div style={{ 
              position: 'absolute', 
              top: '50%', 
              left: '50%', 
              transform: 'translate(-50%, -50%)',
              border: '2px solid #1890ff',
              width: 200,
              height: 200,
              borderRadius: 8,
            }} />
            <Space style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
              <Text type="secondary">請將 QR Code 對準框內</Text>
            </Space>
            <Space style={{ marginTop: 8, width: '100%', justifyContent: 'center' }}>
              <Button onClick={() => setScanning(false)} danger>取消掃描</Button>
            </Space>
          </Card>
        )}

        {manualEntry && (
          <Card>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleManualConfirm}
            >
              <Form.Item
                label="訂單編號"
                name="orderId"
                rules={[{ required: true, message: '請輸入訂單編號' }]}
              >
                <Input 
                  placeholder="例如：ORD20250722-001" 
                  size="large"
                />
              </Form.Item>
              
              <Form.Item
                label="瓦斯桶序號"
                name="cylinderSerial"
                rules={[{ required: true, message: '請輸入瓦斯桶序號' }]}
              >
                <Input 
                  placeholder="請輸入瓦斯桶上的序號" 
                  size="large"
                />
              </Form.Item>

              <Form.Item>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Button onClick={() => setManualEntry(false)}>
                    返回掃描
                  </Button>
                  <Button 
                    type="primary" 
                    htmlType="submit"
                    icon={<CheckCircleOutlined />}
                  >
                    確認配送
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        )}
      </div>
    </div>
  );
};

export default DeliveryScanner;