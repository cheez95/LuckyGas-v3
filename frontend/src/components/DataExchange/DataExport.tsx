import React, { useState } from 'react';
import { Card, Form, Select, DatePicker, Button, Space, message, Radio, Checkbox, Divider } from 'antd';
import { DownloadOutlined, FileExcelOutlined, FileCsvOutlined, FileJsonOutlined } from '@ant-design/icons';
import moment from 'moment';
import { saveAs } from 'file-saver';

const { RangePicker } = DatePicker;
const { Option } = Select;

interface ExportConfig {
  dataType: string;
  format: string;
  dateRange?: [moment.Moment, moment.Moment];
  filters?: Record<string, any>;
  fields?: string[];
}

const DataExport: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedFields, setSelectedFields] = useState<string[]>([]);

  // Field options for different data types
  const fieldOptions: Record<string, { label: string; value: string }[]> = {
    customers: [
      { label: '客戶編號', value: '客戶編號' },
      { label: '客戶名稱', value: '客戶名稱' },
      { label: '電話', value: '電話' },
      { label: '地址', value: '地址' },
      { label: '區域', value: '區域' },
      { label: '客戶類型', value: '客戶類型' },
      { label: '信用額度', value: '信用額度' },
      { label: '付款條件', value: '付款條件' },
      { label: '聯絡人', value: '聯絡人' },
      { label: '電子郵件', value: '電子郵件' },
      { label: '統一編號', value: '統一編號' },
      { label: '狀態', value: '狀態' },
      { label: '建立日期', value: '建立日期' },
      { label: '備註', value: '備註' },
    ],
  };

  const handleExport = async (values: any) => {
    setLoading(true);
    
    try {
      const { dataType, format, dateRange, ...filters } = values;
      
      // Build query parameters
      const params = new URLSearchParams();
      params.append('format', format);
      
      // Add date range if applicable
      if (dateRange && dateRange[0] && dateRange[1]) {
        params.append('start_date', dateRange[0].format('YYYY-MM-DD'));
        params.append('end_date', dateRange[1].format('YYYY-MM-DD'));
      }
      
      // Add filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
      
      // Add selected fields for customers
      if (dataType === 'customers' && selectedFields.length > 0) {
        params.append('fields', selectedFields.join(','));
      }
      
      // Make API request
      const response = await fetch(`/api/v1/data/export/${dataType}?${params}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
      const filename = filenameMatch ? filenameMatch[1] : `export_${dataType}_${moment().format('YYYY-MM-DD')}.${format}`;
      
      // Download file
      const blob = await response.blob();
      saveAs(blob, filename);
      
      message.success('資料匯出成功！');
    } catch (error) {
      console.error('Export error:', error);
      message.error('資料匯出失敗');
    } finally {
      setLoading(false);
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'excel':
        return <FileExcelOutlined />;
      case 'csv':
        return <FileCsvOutlined />;
      case 'json':
        return <FileJsonOutlined />;
      default:
        return <DownloadOutlined />;
    }
  };

  return (
    <Card title="資料匯出" className="data-export-card">
      <Form
        form={form}
        layout="vertical"
        onFinish={handleExport}
        initialValues={{
          dataType: 'customers',
          format: 'excel',
        }}
      >
        <Form.Item
          name="dataType"
          label="資料類型"
          rules={[{ required: true, message: '請選擇資料類型' }]}
        >
          <Select size="large">
            <Option value="customers">客戶資料</Option>
            <Option value="orders">訂單資料</Option>
            <Option value="routes">路線資料</Option>
            <Option value="deliveries">配送記錄</Option>
            <Option value="financial-summary">財務摘要</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="format"
          label="匯出格式"
          rules={[{ required: true, message: '請選擇匯出格式' }]}
        >
          <Radio.Group size="large">
            <Radio.Button value="excel">
              <FileExcelOutlined /> Excel
            </Radio.Button>
            <Radio.Button value="csv">
              <FileCsvOutlined /> CSV
            </Radio.Button>
            <Radio.Button value="json">
              <FileJsonOutlined /> JSON
            </Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          noStyle
          shouldUpdate={(prevValues, currentValues) => 
            prevValues.dataType !== currentValues.dataType
          }
        >
          {({ getFieldValue }) => {
            const dataType = getFieldValue('dataType');
            
            // Show date range for applicable data types
            if (['orders', 'routes', 'deliveries', 'financial-summary'].includes(dataType)) {
              return (
                <Form.Item
                  name="dateRange"
                  label="日期範圍"
                >
                  <RangePicker
                    size="large"
                    style={{ width: '100%' }}
                    placeholder={['開始日期', '結束日期']}
                  />
                </Form.Item>
              );
            }
            
            // Show filters for customers
            if (dataType === 'customers') {
              return (
                <>
                  <Form.Item
                    name="customer_type"
                    label="客戶類型"
                  >
                    <Select allowClear placeholder="全部">
                      <Option value="individual">個人</Option>
                      <Option value="company">公司</Option>
                      <Option value="restaurant">餐廳</Option>
                      <Option value="factory">工廠</Option>
                      <Option value="other">其他</Option>
                    </Select>
                  </Form.Item>
                  
                  <Form.Item
                    name="district"
                    label="區域"
                  >
                    <Select allowClear placeholder="全部">
                      <Option value="中正區">中正區</Option>
                      <Option value="大同區">大同區</Option>
                      <Option value="中山區">中山區</Option>
                      <Option value="松山區">松山區</Option>
                      <Option value="大安區">大安區</Option>
                      <Option value="萬華區">萬華區</Option>
                      <Option value="信義區">信義區</Option>
                      <Option value="士林區">士林區</Option>
                      <Option value="北投區">北投區</Option>
                      <Option value="內湖區">內湖區</Option>
                      <Option value="南港區">南港區</Option>
                      <Option value="文山區">文山區</Option>
                    </Select>
                  </Form.Item>
                  
                  <Form.Item
                    name="is_active"
                    label="狀態"
                  >
                    <Select allowClear placeholder="全部">
                      <Option value={true}>啟用</Option>
                      <Option value={false}>停用</Option>
                    </Select>
                  </Form.Item>
                  
                  <Form.Item label="匯出欄位">
                    <Checkbox.Group
                      options={fieldOptions.customers}
                      value={selectedFields}
                      onChange={setSelectedFields}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Button 
                        size="small" 
                        type="link"
                        onClick={() => setSelectedFields(fieldOptions.customers.map(f => f.value))}
                      >
                        全選
                      </Button>
                      <Button 
                        size="small" 
                        type="link"
                        onClick={() => setSelectedFields([])}
                      >
                        清除
                      </Button>
                    </div>
                  </Form.Item>
                </>
              );
            }
            
            // Show filters for orders
            if (dataType === 'orders') {
              return (
                <Form.Item
                  name="status"
                  label="訂單狀態"
                >
                  <Select allowClear placeholder="全部">
                    <Option value="pending">待處理</Option>
                    <Option value="confirmed">已確認</Option>
                    <Option value="preparing">準備中</Option>
                    <Option value="delivering">配送中</Option>
                    <Option value="delivered">已送達</Option>
                    <Option value="cancelled">已取消</Option>
                  </Select>
                </Form.Item>
              );
            }
            
            return null;
          }}
        </Form.Item>

        <Divider />

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<DownloadOutlined />}
              size="large"
            >
              匯出資料
            </Button>
            <Button
              onClick={() => {
                form.resetFields();
                setSelectedFields([]);
              }}
            >
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Divider />

      <div className="export-notes">
        <h4>注意事項：</h4>
        <ul>
          <li>Excel 格式適合在 Microsoft Excel 或 Google Sheets 中開啟</li>
          <li>CSV 格式適合匯入其他系統，檔案較小</li>
          <li>JSON 格式適合程式化處理</li>
          <li>訂單資料會包含訂單明細，匯出為多個工作表或檔案</li>
          <li>財務摘要僅支援 Excel 格式</li>
        </ul>
      </div>
    </Card>
  );
};

export default DataExport;