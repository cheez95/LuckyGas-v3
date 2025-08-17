import React, { useState } from 'react';
import {
  Card,
  Upload,
  Button,
  Select,
  Form,
  Switch,
  Table,
  Alert,
  Space,
  message,
  Divider,
  Tag,
  Progress,
  Modal,
  Typography,
} from 'antd';
import {
  UploadOutlined,
  FileExcelOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { UploadProps, ColumnsType } from 'antd';

const { Option } = Select;
const { Text } = Typography;
const { Dragger } = Upload;

interface ImportResult {
  total_rows: number;
  created: number;
  updated?: number;
  skipped?: number;
  errors: Array<{
    row?: number;
    field?: string;
    value?: string;
    error: string;
  }>;
  warnings: Array<{
    row?: number;
    message: string;
    action: string;
  }>;
}

const DataImport: React.FC = () => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<any[]>([]);
  const [importing, setImporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [showResultModal, setShowResultModal] = useState(false);

  const handleImport = async (values: any) => {
    if (fileList.length === 0) {
      message.error('請選擇要匯入的檔案');
      return;
    }

    const { dataType, updateExisting, validateOnly } = values;
    const formData = new FormData();
    formData.append('file', fileList[0].originFileObj);

    const setLoadingState = validateOnly ? setValidating : setImporting;
    setLoadingState(true);

    try {
      const params = new URLSearchParams();
      if (updateExisting) params.append('update_existing', 'true');
      if (validateOnly) params.append('validate_only', 'true');

      const response = await fetch(`/api/v1/data/import/${dataType}?${params}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Import failed');
      }

      setImportResult(data.result);
      setShowResultModal(true);

      if (!validateOnly && data.result.errors.length === 0) {
        message.success('資料匯入成功！');
        setFileList([]);
        form.resetFields(['file']);
      }
    } catch (error: any) {
      console.error('Import error:', error);
      message.error(error.message || '匯入失敗');
    } finally {
      setLoadingState(false);
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    fileList,
    beforeUpload: (file) => {
      const isValidType = file.name.endsWith('.csv') || 
                         file.name.endsWith('.xlsx') || 
                         file.name.endsWith('.xls');
      
      if (!isValidType) {
        message.error('只支援 CSV 和 Excel 檔案格式');
        return false;
      }

      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('檔案大小不能超過 10MB');
        return false;
      }

      setFileList([file]);
      return false; // Prevent auto upload
    },
    onRemove: () => {
      setFileList([]);
    },
  };

  const downloadTemplate = async (dataType: string) => {
    try {
      const format = dataType === 'orders' ? 'excel' : 
                     form.getFieldValue('templateFormat') || 'excel';
      
      const response = await fetch(`/api/v1/data/templates/${dataType}?format=${format}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
      const filename = filenameMatch ? filenameMatch[1] : `${dataType}_template.${format}`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      message.success('範本下載成功！');
    } catch (error) {
      console.error('Download error:', error);
      message.error('範本下載失敗');
    }
  };

  const errorColumns: ColumnsType<any> = [
    {
      title: '行號',
      dataIndex: 'row',
      key: 'row',
      width: 80,
    },
    {
      title: '欄位',
      dataIndex: 'field',
      key: 'field',
      width: 120,
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
      width: 150,
      ellipsis: true,
    },
    {
      title: '錯誤訊息',
      dataIndex: 'error',
      key: 'error',
    },
  ];

  const warningColumns: ColumnsType<any> = [
    {
      title: '行號',
      dataIndex: 'row',
      key: 'row',
      width: 80,
    },
    {
      title: '警告訊息',
      dataIndex: 'message',
      key: 'message',
    },
    {
      title: '處理方式',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action: string) => (
        <Tag color="orange">{action}</Tag>
      ),
    },
  ];

  return (
    <Card title="資料匯入" className="data-import-card">
      <Form
        form={form}
        layout="vertical"
        onFinish={handleImport}
        initialValues={{
          dataType: 'customers',
          updateExisting: false,
          validateOnly: false,
        }}
      >
        <Form.Item
          name="dataType"
          label="資料類型"
          rules={[{ required: true, message: '請選擇資料類型' }]}
        >
          <Select size="large" onChange={() => setFileList([])}>
            <Option value="customers">客戶資料</Option>
            <Option value="products">產品資料</Option>
            <Option value="orders">訂單資料</Option>
          </Select>
        </Form.Item>

        <Form.Item
          noStyle
          shouldUpdate={(prevValues, currentValues) => 
            prevValues.dataType !== currentValues.dataType
          }
        >
          {({ getFieldValue }) => {
            const dataType = getFieldValue('dataType');
            
            return (
              <Form.Item label="下載範本">
                <Space>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={() => downloadTemplate(dataType)}
                  >
                    下載 Excel 範本
                  </Button>
                  {dataType !== 'orders' && (
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => {
                        form.setFieldsValue({ templateFormat: 'csv' });
                        downloadTemplate(dataType);
                      }}
                    >
                      下載 CSV 範本
                    </Button>
                  )}
                </Space>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    請先下載範本，按照範本格式準備資料
                  </Text>
                </div>
              </Form.Item>
            );
          }}
        </Form.Item>

        <Form.Item
          name="file"
          label="選擇檔案"
          rules={[{ required: true, message: '請選擇檔案' }]}
        >
          <Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <FileExcelOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">點擊或拖曳檔案到此區域</p>
            <p className="ant-upload-hint">
              支援 CSV 和 Excel (.xlsx, .xls) 格式，檔案大小不超過 10MB
            </p>
          </Dragger>
        </Form.Item>

        <Form.Item
          noStyle
          shouldUpdate={(prevValues, currentValues) => 
            prevValues.dataType !== currentValues.dataType
          }
        >
          {({ getFieldValue }) => {
            const dataType = getFieldValue('dataType');
            
            if (dataType === 'orders') {
              return (
                <Alert
                  message="訂單匯入說明"
                  description="訂單匯入需要 Excel 檔案，包含'訂單'和'訂單明細'兩個工作表"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              );
            }
            
            return (
              <Form.Item
                name="updateExisting"
                label="更新現有資料"
                valuePropName="checked"
              >
                <Switch />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    開啟後，如果資料已存在將會更新，否則跳過
                  </Text>
                </div>
              </Form.Item>
            );
          }}
        </Form.Item>

        <Divider />

        <Form.Item>
          <Space>
            <Button
              onClick={() => form.setFieldsValue({ validateOnly: true })}
              loading={validating}
              disabled={fileList.length === 0}
            >
              驗證資料
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              icon={<UploadOutlined />}
              loading={importing}
              disabled={fileList.length === 0}
            >
              匯入資料
            </Button>
            <Button
              onClick={() => {
                form.resetFields();
                setFileList([]);
                setImportResult(null);
              }}
            >
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Modal
        title="匯入結果"
        visible={showResultModal}
        onCancel={() => setShowResultModal(false)}
        footer={[
          <Button key="close" onClick={() => setShowResultModal(false)}>
            關閉
          </Button>,
        ]}
        width={800}
      >
        {importResult && (
          <div>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <Space size="large">
                  <div>
                    <Text type="secondary">總筆數：</Text>
                    <Text strong>{importResult.total_rows}</Text>
                  </div>
                  <div>
                    <Text type="secondary">新增：</Text>
                    <Text strong style={{ color: '#52c41a' }}>
                      {importResult.created}
                    </Text>
                  </div>
                  {importResult.updated !== undefined && (
                    <div>
                      <Text type="secondary">更新：</Text>
                      <Text strong style={{ color: '#1890ff' }}>
                        {importResult.updated}
                      </Text>
                    </div>
                  )}
                  {importResult.skipped !== undefined && (
                    <div>
                      <Text type="secondary">跳過：</Text>
                      <Text strong style={{ color: '#faad14' }}>
                        {importResult.skipped}
                      </Text>
                    </div>
                  )}
                </Space>
              </div>

              {importResult.errors.length > 0 && (
                <div>
                  <Alert
                    message={`發現 ${importResult.errors.length} 個錯誤`}
                    type="error"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <Table
                    dataSource={importResult.errors}
                    columns={errorColumns}
                    pagination={{ pageSize: 5 }}
                    size="small"
                    rowKey={(record, index) => index!}
                  />
                </div>
              )}

              {importResult.warnings.length > 0 && (
                <div>
                  <Alert
                    message={`發現 ${importResult.warnings.length} 個警告`}
                    type="warning"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <Table
                    dataSource={importResult.warnings}
                    columns={warningColumns}
                    pagination={{ pageSize: 5 }}
                    size="small"
                    rowKey={(record, index) => index!}
                  />
                </div>
              )}

              {importResult.errors.length === 0 && importResult.warnings.length === 0 && (
                <Alert
                  message="匯入成功"
                  description="所有資料都已成功匯入，沒有發現錯誤或警告"
                  type="success"
                  showIcon
                />
              )}
            </Space>
          </div>
        )}
      </Modal>
    </Card>
  );
};

export default DataImport;