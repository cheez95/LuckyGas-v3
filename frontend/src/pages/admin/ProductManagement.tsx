import React, { useState, useEffect } from 'react';
import { Card, Button, Space, message, Modal, Upload, Tabs } from 'antd';
import { PlusOutlined, UploadOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { UploadProps } from 'antd';
import ProductList from '../../components/admin/ProductList';
import ProductForm from '../../components/admin/ProductForm';
import ProductService from '../../services/product.service';
import { GasProduct, GasProductCreate, GasProductUpdate } from '../../types/product';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const { TabPane } = Tabs;

const ProductManagement: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [products, setProducts] = useState<GasProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<GasProduct | null>(null);
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [isImportModalVisible, setIsImportModalVisible] = useState(false);
  const [importLoading, setImportLoading] = useState(false);

  // Check authorization
  useEffect(() => {
    if (!user || !['super_admin', 'manager'].includes(user.role)) {
      message.error('您沒有權限訪問此頁面');
      navigate('/');
    }
  }, [user, navigate]);

  // Load products
  const loadProducts = async () => {
    setLoading(true);
    try {
      const response = await ProductService.getProducts({ limit: 1000 });
      setProducts(response.items);
    } catch (error) {
      message.error('載入產品資料失敗');
      console.error('Failed to load products:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  // Handle CRUD operations
  const handleAdd = () => {
    setSelectedProduct(null);
    setIsFormVisible(true);
  };

  const handleEdit = (product: GasProduct) => {
    setSelectedProduct(product);
    setIsFormVisible(true);
  };

  const handleDelete = async (product: GasProduct) => {
    Modal.confirm({
      title: '確認刪除',
      content: `確定要刪除產品「${product.display_name}」嗎？`,
      okText: '確定',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await ProductService.deleteProduct(product.id);
          message.success('產品已刪除');
          loadProducts();
        } catch (error) {
          message.error('刪除產品失敗');
          console.error('Failed to delete product:', error);
        }
      },
    });
  };

  const handleFormSubmit = async (values: GasProductCreate | GasProductUpdate) => {
    try {
      if (selectedProduct) {
        // Update existing product
        await ProductService.updateProduct(selectedProduct.id, values as GasProductUpdate);
        message.success('產品已更新');
      } else {
        // Create new product
        await ProductService.createProduct(values as GasProductCreate);
        message.success('產品已新增');
      }
      setIsFormVisible(false);
      loadProducts();
    } catch (error) {
      message.error(selectedProduct ? '更新產品失敗' : '新增產品失敗');
      console.error('Failed to save product:', error);
    }
  };

  const handleFormCancel = () => {
    setIsFormVisible(false);
    setSelectedProduct(null);
  };

  // Handle Excel import
  const handleImport = () => {
    setIsImportModalVisible(true);
  };

  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.xlsx,.xls',
    beforeUpload: async (file) => {
      setImportLoading(true);
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/api/v1/products/import', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          message.success(`成功匯入 ${result.imported_count} 個產品`);
          setIsImportModalVisible(false);
          loadProducts();
        } else {
          const error = await response.json();
          message.error(`匯入失敗: ${error.detail || '未知錯誤'}`);
        }
      } catch (error) {
        message.error('匯入失敗');
        console.error('Import failed:', error);
      } finally {
        setImportLoading(false);
      }

      return false; // Prevent default upload
    },
  };

  // Handle Excel export
  const handleExport = async () => {
    try {
      const response = await fetch('/api/v1/products/export', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `products_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        message.success('產品資料已匯出');
      } else {
        message.error('匯出失敗');
      }
    } catch (error) {
      message.error('匯出失敗');
      console.error('Export failed:', error);
    }
  };

  return (
    <Card
      title="產品管理"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadProducts} loading={loading}>
            重新整理
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            匯出 Excel
          </Button>
          <Button icon={<UploadOutlined />} onClick={handleImport}>
            匯入 Excel
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增產品
          </Button>
        </Space>
      }
    >
      <Tabs defaultActiveKey="all">
        <TabPane tab="所有產品" key="all">
          <ProductList
            products={products}
            loading={loading}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onRefresh={loadProducts}
          />
        </TabPane>
        <TabPane tab="啟用中" key="active">
          <ProductList
            products={products.filter(p => p.is_active)}
            loading={loading}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onRefresh={loadProducts}
          />
        </TabPane>
        <TabPane tab="停用中" key="inactive">
          <ProductList
            products={products.filter(p => !p.is_active)}
            loading={loading}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onRefresh={loadProducts}
          />
        </TabPane>
      </Tabs>

      <ProductForm
        visible={isFormVisible}
        product={selectedProduct}
        onSubmit={handleFormSubmit}
        onCancel={handleFormCancel}
      />

      <Modal
        title="匯入產品資料"
        open={isImportModalVisible}
        onCancel={() => setIsImportModalVisible(false)}
        footer={null}
      >
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />} loading={importLoading}>
            選擇 Excel 檔案
          </Button>
        </Upload>
        <div style={{ marginTop: 16, color: '#666' }}>
          <p>請確保 Excel 檔案包含以下欄位：</p>
          <ul>
            <li>配送方式 (CYLINDER/FLOW)</li>
            <li>規格 (4/10/16/20/50)</li>
            <li>屬性 (REGULAR/COMMERCIAL/HAOYUN/PINGAN/XINGFU/SPECIAL)</li>
            <li>產品編號</li>
            <li>中文名稱</li>
            <li>單價</li>
            <li>押金</li>
          </ul>
        </div>
      </Modal>
    </Card>
  );
};

export default ProductManagement;