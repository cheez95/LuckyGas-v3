import React, { useRef, useState, useEffect } from 'react';
import { Upload, Button, Image, message, Space, Card, Progress, Tag } from 'antd';
import { 
  CameraOutlined, DeleteOutlined, PlusOutlined, 
  CloudUploadOutlined, WifiOutlined, SaveOutlined,
  CompressOutlined
} from '@ant-design/icons';
import imageCompression from 'browser-image-compression';
import type { UploadFile } from 'antd/es/upload/interface';
import mobileService from '../../services/mobile.service';

interface EnhancedPhotoCaptureProps {
  onCapture: (photos: string[]) => void;
  maxPhotos?: number;
  maxSizeMB?: number;
  enableOfflineQueue?: boolean;
  deliveryId?: string | number;
  requireGeoTag?: boolean;
}

interface PhotoMetadata {
  timestamp: string;
  location?: {
    latitude: number;
    longitude: number;
    accuracy: number;
  };
  deviceInfo?: {
    userAgent: string;
    platform: string;
  };
  compressionRatio?: number;
  originalSize?: number;
  compressedSize?: number;
}

const EnhancedPhotoCapture: React.FC<EnhancedPhotoCaptureProps> = ({
  onCapture,
  maxPhotos = 3,
  maxSizeMB = 1,
  enableOfflineQueue = true,
  deliveryId,
  requireGeoTag = true,
}) => {
  const [photos, setPhotos] = useState<UploadFile[]>([]);
  const [compressing, setCompressing] = useState(false);
  const [isOnline, setIsOnline] = useState(mobileService.isDeviceOnline());
  const [compressionProgress, setCompressionProgress] = useState(0);
  const [offlinePhotoCount, setOfflinePhotoCount] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [usingCamera, setUsingCamera] = useState(false);

  useEffect(() => {
    // Monitor online status
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    // Check offline queue
    setOfflinePhotoCount(mobileService.getOfflineQueueCount());
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      stopCamera();
    };
  }, []);

  // Get current location for geotagging
  const getCurrentLocation = async (): Promise<PhotoMetadata['location'] | undefined> => {
    if (!requireGeoTag) return undefined;

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          });
        },
        (error) => {
          console.error('Failed to get location for photo:', error);
          resolve(undefined);
        },
        { enableHighAccuracy: true, timeout: 5000 }
      );
    });
  };

  // Compress image with progress tracking
  const compressImage = async (file: File): Promise<{ compressed: string; metadata: PhotoMetadata }> => {
    const originalSize = file.size;
    
    const options = {
      maxSizeMB,
      maxWidthOrHeight: 1920,
      useWebWorker: true,
      fileType: 'image/jpeg' as const,
      quality: 0.8,
      onProgress: (progress: number) => {
        setCompressionProgress(progress);
      },
    };

    try {
      const compressedFile = await imageCompression(file, options);
      const compressedSize = compressedFile.size;
      
      // Convert to base64
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(compressedFile);
      });

      // Get location and create metadata
      const location = await getCurrentLocation();
      const metadata: PhotoMetadata = {
        timestamp: new Date().toISOString(),
        location,
        deviceInfo: {
          userAgent: navigator.userAgent,
          platform: navigator.platform,
        },
        compressionRatio: ((originalSize - compressedSize) / originalSize * 100),
        originalSize,
        compressedSize,
      };

      return { compressed: base64, metadata };
    } catch (error) {
      console.error('Image compression failed:', error);
      throw error;
    }
  };

  // Start camera for direct capture
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          facingMode: 'environment', // Use rear camera
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraStream(stream);
        setUsingCamera(true);
      }
    } catch (error) {
      console.error('Failed to start camera:', error);
      message.error('無法啟動相機');
    }
  };

  // Stop camera
  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
      setUsingCamera(false);
    }
  };

  // Capture photo from camera
  const captureFromCamera = async () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    if (!context) return;

    // Set canvas size to video size
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw video frame to canvas
    context.drawImage(video, 0, 0);
    
    // Convert canvas to blob
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      
      const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
      await handleCapture(file);
    }, 'image/jpeg', 0.8);
  };

  // Handle photo capture
  const handleCapture = async (file: File) => {
    if (photos.length >= maxPhotos) {
      message.warning(`最多只能上傳 ${maxPhotos} 張照片`);
      return false;
    }

    setCompressing(true);
    setCompressionProgress(0);
    
    try {
      const { compressed, metadata } = await compressImage(file);
      
      const newPhoto: UploadFile = {
        uid: Date.now().toString(),
        name: file.name,
        status: 'done',
        url: compressed,
        thumbUrl: compressed,
        response: metadata, // Store metadata in response field
      };

      const updatedPhotos = [...photos, newPhoto];
      setPhotos(updatedPhotos);
      onCapture(updatedPhotos.map(p => p.url || ''));
      
      // Queue for offline upload if needed
      if (enableOfflineQueue && !isOnline) {
        mobileService.addToOfflineQueue('photo_upload', {
          photo: compressed,
          metadata: {
            ...metadata,
            deliveryId,
          },
        });
        setOfflinePhotoCount(prev => prev + 1);
        message.info('照片已儲存，將在恢復連線後上傳');
      } else {
        message.success('照片已上傳');
      }
    } catch (error) {
      message.error('照片處理失敗');
    } finally {
      setCompressing(false);
      setCompressionProgress(0);
    }

    return false;
  };

  // Remove photo
  const removePhoto = (uid: string) => {
    const updatedPhotos = photos.filter(p => p.uid !== uid);
    setPhotos(updatedPhotos);
    onCapture(updatedPhotos.map(p => p.url || ''));
  };

  // Mobile camera capture support
  const handleMobileCapture = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.multiple = true;
    input.max = String(maxPhotos - photos.length);
    
    input.onchange = async (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (!files) return;

      for (let i = 0; i < files.length && photos.length + i < maxPhotos; i++) {
        await handleCapture(files[i]);
      }
    };

    input.click();
  };

  // Sync offline photos
  const syncOfflinePhotos = async () => {
    if (!isOnline) {
      message.warning('請在有網路連線時同步');
      return;
    }

    message.loading('正在同步離線照片...');
    await mobileService.processOfflineQueue();
    setOfflinePhotoCount(mobileService.getOfflineQueueCount());
    message.success('離線照片同步完成');
  };

  return (
    <div className="enhanced-photo-capture">
      <Space direction="vertical" style={{ width: '100%' }}>
        {/* Status indicators */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Tag icon={<WifiOutlined />} color={isOnline ? 'success' : 'error'}>
              {isOnline ? '線上' : '離線'}
            </Tag>
            {offlinePhotoCount > 0 && (
              <Tag icon={<SaveOutlined />} color="warning">
                {offlinePhotoCount} 張待同步
              </Tag>
            )}
          </Space>
          {offlinePhotoCount > 0 && isOnline && (
            <Button 
              size="small" 
              icon={<CloudUploadOutlined />} 
              onClick={syncOfflinePhotos}
            >
              同步
            </Button>
          )}
        </div>

        {/* Camera preview */}
        {usingCamera && (
          <Card>
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline
              style={{ width: '100%', maxHeight: 400 }}
            />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <Space style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
              <Button
                type="primary"
                icon={<CameraOutlined />}
                onClick={captureFromCamera}
                size="large"
              >
                拍照
              </Button>
              <Button onClick={stopCamera}>
                關閉相機
              </Button>
            </Space>
          </Card>
        )}

        {/* Capture buttons */}
        {!usingCamera && (
          <Space style={{ width: '100%' }}>
            <Button
              type="primary"
              icon={<CameraOutlined />}
              onClick={handleMobileCapture}
              block
              size="large"
              loading={compressing}
              disabled={photos.length >= maxPhotos}
              style={{ flex: 1 }}
            >
              拍攝配送照片 ({photos.length}/{maxPhotos})
            </Button>
            <Button
              icon={<CameraOutlined />}
              onClick={startCamera}
              size="large"
            >
              即時拍攝
            </Button>
          </Space>
        )}

        {/* Compression progress */}
        {compressing && (
          <Card size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <CompressOutlined />
                <span>正在壓縮照片...</span>
              </Space>
              <Progress percent={compressionProgress} size="small" />
            </Space>
          </Card>
        )}

        {/* Photo gallery */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
          gap: 8,
          marginTop: 16 
        }}>
          {photos.map((photo) => {
            const metadata = photo.response as PhotoMetadata;
            return (
              <Card
                key={photo.uid}
                cover={
                  <Image
                    src={photo.url}
                    alt={photo.name}
                    style={{ height: 100, objectFit: 'cover' }}
                  />
                }
                size="small"
                actions={[
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => removePhoto(photo.uid)}
                    size="small"
                  />,
                ]}
              >
                {metadata?.location && (
                  <div style={{ fontSize: 10, color: '#999' }}>
                    📍 已標記位置
                  </div>
                )}
                {metadata?.compressionRatio && (
                  <div style={{ fontSize: 10, color: '#999' }}>
                    壓縮 {metadata.compressionRatio.toFixed(0)}%
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        {/* Desktop upload (fallback) */}
        {photos.length < maxPhotos && !usingCamera && (
          <Upload
            accept="image/*"
            beforeUpload={handleCapture}
            showUploadList={false}
            multiple={false}
            className="photo-upload-desktop"
          >
            <Button icon={<PlusOutlined />} disabled={compressing}>
              從電腦選擇照片
            </Button>
          </Upload>
        )}
      </Space>

      <style jsx>{`
        .enhanced-photo-capture {
          width: 100%;
        }
        
        @media (max-width: 768px) {
          .photo-upload-desktop {
            display: none;
          }
        }
      `}</style>
    </div>
  );
};

export default EnhancedPhotoCapture;