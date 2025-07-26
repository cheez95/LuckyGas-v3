import React, { useState, useEffect } from 'react';
import { Select, Space, Tag, Button, message } from 'antd';
import { FileTextOutlined, CalendarOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Option } = Select;

interface TemplateQuickSelectProps {
  customerId: number | null;
  onTemplateSelect: (template: any) => void;
  disabled?: boolean;
}

const TemplateQuickSelect: React.FC<TemplateQuickSelectProps> = ({
  customerId,
  onTemplateSelect,
  disabled = false
}) => {
  const { t } = useTranslation();
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);

  useEffect(() => {
    if (customerId) {
      fetchCustomerTemplates();
    } else {
      setTemplates([]);
      setSelectedTemplateId(null);
    }
  }, [customerId]);

  const fetchCustomerTemplates = async () => {
    if (!customerId) return;
    
    setLoading(true);
    try {
      const response = await api.get(`/order-templates/customer/${customerId}/templates`);
      setTemplates(response.data);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateSelect = (templateId: number) => {
    setSelectedTemplateId(templateId);
    const template = templates.find(t => t.id === templateId);
    if (template) {
      onTemplateSelect(template);
      message.success(t('orders.templates.templateApplied'));
    }
  };

  const handleCreateOrderFromTemplate = async (templateId: number) => {
    try {
      const response = await api.post('/order-templates/create-order', {
        template_id: templateId
      });
      message.success(t('orders.templates.orderCreated'));
      // You might want to redirect to the created order or refresh the order list
    } catch (error) {
      message.error(t('orders.templates.orderCreateError'));
    }
  };

  if (!customerId || templates.length === 0) {
    return null;
  }

  return (
    <Space style={{ width: '100%' }}>
      <FileTextOutlined />
      <Select
        style={{ width: 300 }}
        placeholder={t('orders.templates.selectTemplate')}
        loading={loading}
        disabled={disabled}
        value={selectedTemplateId}
        onChange={handleTemplateSelect}
        allowClear
      >
        {templates.map(template => (
          <Option key={template.id} value={template.id}>
            <Space>
              <span>{template.template_name}</span>
              {template.is_recurring && (
                <Tag color="blue" icon={<CalendarOutlined />}>
                  {t(`orders.templates.recurrence.${template.recurrence_pattern}`)}
                </Tag>
              )}
              <Tag>{t('orders.templates.timesUsed', { count: template.times_used })}</Tag>
            </Space>
          </Option>
        ))}
      </Select>
      {selectedTemplateId && (
        <Button
          type="link"
          onClick={() => handleCreateOrderFromTemplate(selectedTemplateId)}
        >
          {t('orders.templates.quickCreate')}
        </Button>
      )}
    </Space>
  );
};

export default TemplateQuickSelect;