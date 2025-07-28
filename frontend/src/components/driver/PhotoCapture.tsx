import React, { useRef, useState } from 'react';
import { Upload, Button, Image, message, Space, Card } from 'antd';
import { CameraOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import imageCompression from 'browser-image-compression';
import type { UploadFile } from 'antd/es/upload/interface';

interface PhotoCaptureProps {
  onCapture: (photos: string[]) => void;
  maxPhotos?: number;
  maxSizeMB?: number;
}

const PhotoCapture: React.FC<PhotoCaptureProps> = ({
  onCapture,
  maxPhotos = 3,
  maxSizeMB = 1,
}) => {
  const [photos, setPhotos] = useState<UploadFile[]>([]);
  const [compressing, setCompressing] = useState(false);

  const compressImage = async (file: File): Promise<string> => {
    const options = {
      maxSizeMB,
      maxWidthOrHeight: 1920,
      useWebWorker: true,
      fileType: 'image/jpeg',
      quality: 0.8,
    };

    try {
      const compressedFile = await imageCompression(file, options);
      
      // Convert to base64
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(compressedFile);
      });
    } catch (error) {
      console.error('Image compression failed:', error);
      throw error;
    }
  };

  const handleCapture = async (file: File) => {
    if (photos.length >= maxPhotos) {
      message.warning(`最多只能上傳 ${maxPhotos} 張照片`);
      return false;
    }

    setCompressing(true);
    try {
      const compressed = await compressImage(file);
      
      const newPhoto: UploadFile = {
        uid: Date.now().toString(),
        name: file.name,
        status: 'done',
        url: compressed,
        thumbUrl: compressed,
      };

      const updatedPhotos = [...photos, newPhoto];
      setPhotos(updatedPhotos);
      onCapture(updatedPhotos.map(p => p.url || ''));
      
      message.success('照片已上傳');
    } catch (error) {
      message.error('照片處理失敗');
    } finally {
      setCompressing(false);
    }

    return false; // Prevent default upload
  };

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
    input.capture = 'environment'; // Use rear camera
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

  return (
    <div className="photo-capture">
      <Space direction="vertical" style={{ width: '100%' }}>
        {/* Mobile-friendly camera button */}
        <Button
          type="primary"
          icon={<CameraOutlined />}
          onClick={handleMobileCapture}
          block
          size="large"
          loading={compressing}
          disabled={photos.length >= maxPhotos}
        >
          拍攝配送照片 ({photos.length}/{maxPhotos})
        </Button>

        {/* Photo gallery */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
          gap: 8,
          marginTop: 16 
        }}>
          {photos.map((photo) => (
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
            />
          ))}
        </div>

        {/* Desktop upload (fallback) */}
        {photos.length < maxPhotos && (
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
        .photo-capture {
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

export default PhotoCapture;