import React, { useRef, useState } from 'react';
import { Button, Space, Modal } from 'antd';
import { CameraOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import './PhotoCapture.css';

interface PhotoCaptureProps {
  onPhoto: (photo: string | null) => void;
  photo: string | null;
}

const PhotoCapture: React.FC<PhotoCaptureProps> = ({ onPhoto, photo }) => {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraVisible, setCameraVisible] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      return;
    }

    // Read and compress image
    const reader = new FileReader();
    reader.onload = (e) => {
      compressImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const compressImage = (dataUrl: string) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Calculate new dimensions (max 800px width)
      const maxWidth = 800;
      const scale = maxWidth / img.width;
      const newWidth = img.width > maxWidth ? maxWidth : img.width;
      const newHeight = img.width > maxWidth ? img.height * scale : img.height;

      canvas.width = newWidth;
      canvas.height = newHeight;

      // Draw and compress
      ctx.drawImage(img, 0, 0, newWidth, newHeight);
      const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.8);
      onPhoto(compressedDataUrl);
    };
    img.src = dataUrl;
  };

  const openCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, // Use back camera
        audio: false
      });
      
      setStream(mediaStream);
      setCameraVisible(true);
      
      // Wait for modal to open then set video stream
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      }, 100);
    } catch (error) {
      console.error('Camera error:', error);
      // Fall back to file input
      fileInputRef.current?.click();
    }
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;

    const canvas = document.createElement('canvas');
    const video = videoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
      onPhoto(dataUrl);
      closeCamera();
    }
  };

  const closeCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setCameraVisible(false);
  };

  const removePhoto = () => {
    onPhoto(null);
  };

  return (
    <div className="photo-capture">
      {photo ? (
        <div className="photo-preview-container">
          <img
            src={photo}
            alt="Delivery proof"
            className="photo-preview"
            data-testid="photo-preview"
          />
          <Space className="photo-controls">
            <Button
              icon={<ReloadOutlined />}
              onClick={openCamera}
              data-testid="retake-button"
            >
              {t('driver.photo.retake')}
            </Button>
            <Button
              icon={<DeleteOutlined />}
              danger
              onClick={removePhoto}
            >
              {t('driver.photo.remove')}
            </Button>
          </Space>
        </div>
      ) : (
        <div className="photo-placeholder">
          <Button
            type="dashed"
            icon={<CameraOutlined />}
            size="large"
            block
            onClick={openCamera}
            className="take-photo-button"
            data-testid="take-photo-button"
          >
            {t('driver.photo.takePhoto')}
          </Button>
          
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>
      )}

      {/* Camera Modal */}
      <Modal
        title={t('driver.photo.camera')}
        open={cameraVisible}
        onCancel={closeCamera}
        footer={null}
        width="100%"
        className="camera-modal"
        data-testid="camera-preview"
      >
        <div className="camera-container">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="camera-video"
          />
          <div className="camera-controls">
            <Button
              type="primary"
              shape="circle"
              size="large"
              icon={<CameraOutlined />}
              onClick={capturePhoto}
              className="capture-button"
              data-testid="capture-button"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default PhotoCapture;