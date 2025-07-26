import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Select, DatePicker, Button, Space, Row, Col, Tag, Collapse, AutoComplete } from 'antd';
import { SearchOutlined, ClearOutlined, SaveOutlined, HistoryOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Panel } = Collapse;

export interface SearchCriteria {
  keyword?: string;
  dateRange?: [string, string];
  status?: string[];
  priority?: string[];
  paymentStatus?: string[];
  paymentMethod?: string[];
  customerId?: string;
  driverId?: string;
  cylinderType?: string[];
  minAmount?: number;
  maxAmount?: number;
  region?: string;
  customerType?: string;
}

interface SavedSearch {
  id: string;
  name: string;
  criteria: SearchCriteria;
  createdAt: string;
}

interface OrderSearchPanelProps {
  onSearch: (criteria: SearchCriteria) => void;
  onExport?: (criteria: SearchCriteria) => void;
  customers?: any[];
  drivers?: any[];
  loading?: boolean;
}

const OrderSearchPanel: React.FC<OrderSearchPanelProps> = ({
  onSearch,
  onExport,
  customers = [],
  drivers = [],
  loading = false,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [saveSearchModalVisible, setSaveSearchModalVisible] = useState(false);

  useEffect(() => {
    // Load search history and saved searches from localStorage
    const history = localStorage.getItem('orderSearchHistory');
    const saved = localStorage.getItem('savedOrderSearches');
    
    if (history) {
      setSearchHistory(JSON.parse(history));
    }
    
    if (saved) {
      setSavedSearches(JSON.parse(saved));
    }
  }, []);

  const handleSearch = () => {
    const values = form.getFieldsValue();
    const criteria: SearchCriteria = {
      keyword: values.keyword,
      dateRange: values.dateRange ? [
        values.dateRange[0].format('YYYY-MM-DD'),
        values.dateRange[1].format('YYYY-MM-DD')
      ] : undefined,
      status: values.status,
      priority: values.priority,
      paymentStatus: values.paymentStatus,
      paymentMethod: values.paymentMethod,
      customerId: values.customerId,
      driverId: values.driverId,
      cylinderType: values.cylinderType,
      minAmount: values.minAmount,
      maxAmount: values.maxAmount,
      region: values.region,
      customerType: values.customerType,
    };

    // Save to search history
    if (values.keyword) {
      const newHistory = [values.keyword, ...searchHistory.filter(h => h !== values.keyword)].slice(0, 10);
      setSearchHistory(newHistory);
      localStorage.setItem('orderSearchHistory', JSON.stringify(newHistory));
    }

    onSearch(criteria);
  };

  const handleReset = () => {
    form.resetFields();
    onSearch({});
  };

  const handleSaveSearch = () => {
    const values = form.getFieldsValue();
    const searchName = prompt(t('orders.enterSearchName'));
    
    if (searchName) {
      const newSearch: SavedSearch = {
        id: Date.now().toString(),
        name: searchName,
        criteria: values,
        createdAt: new Date().toISOString(),
      };
      
      const updated = [...savedSearches, newSearch];
      setSavedSearches(updated);
      localStorage.setItem('savedOrderSearches', JSON.stringify(updated));
    }
  };

  const handleLoadSavedSearch = (search: SavedSearch) => {
    form.setFieldsValue({
      ...search.criteria,
      dateRange: search.criteria.dateRange 
        ? [dayjs(search.criteria.dateRange[0]), dayjs(search.criteria.dateRange[1])]
        : undefined,
    });
    handleSearch();
  };

  const handleDeleteSavedSearch = (id: string) => {
    const updated = savedSearches.filter(s => s.id !== id);
    setSavedSearches(updated);
    localStorage.setItem('savedOrderSearches', JSON.stringify(updated));
  };

  return (
    <Card className="mb-4">
      <Form form={form} layout="vertical" onFinish={handleSearch}>
        {/* Basic Search */}
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8}>
            <Form.Item name="keyword" label={t('orders.searchKeyword')}>
              <AutoComplete
                placeholder={t('orders.searchPlaceholder')}
                options={searchHistory.map(keyword => ({ value: keyword }))}
                filterOption={(inputValue, option) =>
                  option!.value.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
                }
              >
                <Input prefix={<SearchOutlined />} />
              </AutoComplete>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Form.Item name="dateRange" label={t('orders.dateRange')}>
              <RangePicker 
                style={{ width: '100%' }}
                placeholder={[t('common.startDate'), t('common.endDate')]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Form.Item name="status" label={t('orders.status')}>
              <Select
                mode="multiple"
                placeholder={t('orders.selectStatus')}
                allowClear
              >
                <Option value="pending">{t('orders.statusPending')}</Option>
                <Option value="confirmed">{t('orders.statusConfirmed')}</Option>
                <Option value="assigned">{t('orders.statusAssigned')}</Option>
                <Option value="in_delivery">{t('orders.statusInDelivery')}</Option>
                <Option value="delivered">{t('orders.statusDelivered')}</Option>
                <Option value="cancelled">{t('orders.statusCancelled')}</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        {/* Advanced Search */}
        <Collapse 
          activeKey={isAdvancedOpen ? ['advanced'] : []}
          onChange={(keys) => setIsAdvancedOpen(keys.includes('advanced'))}
        >
          <Panel header={t('orders.advancedSearch')} key="advanced">
            <Row gutter={16}>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="priority" label={t('orders.priority')}>
                  <Select
                    mode="multiple"
                    placeholder={t('orders.selectPriority')}
                    allowClear
                  >
                    <Option value="normal">{t('orders.priorityNormal')}</Option>
                    <Option value="urgent">{t('orders.priorityUrgent')}</Option>
                    <Option value="scheduled">{t('orders.priorityScheduled')}</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="paymentStatus" label={t('orders.paymentStatus')}>
                  <Select
                    mode="multiple"
                    placeholder={t('orders.selectPaymentStatus')}
                    allowClear
                  >
                    <Option value="pending">{t('orders.paymentPending')}</Option>
                    <Option value="paid">{t('orders.paymentPaid')}</Option>
                    <Option value="partial">{t('orders.paymentPartial')}</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="paymentMethod" label={t('orders.paymentMethod')}>
                  <Select
                    mode="multiple"
                    placeholder={t('orders.selectPaymentMethod')}
                    allowClear
                  >
                    <Option value="cash">{t('orders.paymentCash')}</Option>
                    <Option value="transfer">{t('orders.paymentTransfer')}</Option>
                    <Option value="credit">{t('orders.paymentCredit')}</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="cylinderType" label={t('orders.cylinderType')}>
                  <Select
                    mode="multiple"
                    placeholder={t('orders.selectCylinderType')}
                    allowClear
                  >
                    <Option value="4kg">4kg</Option>
                    <Option value="10kg">10kg</Option>
                    <Option value="16kg">16kg</Option>
                    <Option value="20kg">20kg</Option>
                    <Option value="50kg">50kg</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="customerId" label={t('orders.customer')}>
                  <Select
                    showSearch
                    placeholder={t('orders.selectCustomer')}
                    optionFilterProp="children"
                    allowClear
                  >
                    {customers.map(customer => (
                      <Option key={customer.id} value={customer.id}>
                        {customer.name} ({customer.code})
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="driverId" label={t('orders.driver')}>
                  <Select
                    showSearch
                    placeholder={t('orders.selectDriver')}
                    optionFilterProp="children"
                    allowClear
                  >
                    {drivers.map(driver => (
                      <Option key={driver.id} value={driver.id}>
                        {driver.name}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="minAmount" label={t('orders.minAmount')}>
                  <Input type="number" placeholder={t('orders.minAmountPlaceholder')} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="maxAmount" label={t('orders.maxAmount')}>
                  <Input type="number" placeholder={t('orders.maxAmountPlaceholder')} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="region" label={t('orders.region')}>
                  <Select placeholder={t('orders.selectRegion')} allowClear>
                    <Option value="north">{t('orders.regionNorth')}</Option>
                    <Option value="south">{t('orders.regionSouth')}</Option>
                    <Option value="east">{t('orders.regionEast')}</Option>
                    <Option value="west">{t('orders.regionWest')}</Option>
                    <Option value="central">{t('orders.regionCentral')}</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Form.Item name="customerType" label={t('orders.customerType')}>
                  <Select placeholder={t('orders.selectCustomerType')} allowClear>
                    <Option value="household">{t('orders.customerHousehold')}</Option>
                    <Option value="restaurant">{t('orders.customerRestaurant')}</Option>
                    <Option value="industrial">{t('orders.customerIndustrial')}</Option>
                    <Option value="commercial">{t('orders.customerCommercial')}</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
          </Panel>
        </Collapse>

        {/* Action Buttons */}
        <Row gutter={16} className="mt-4">
          <Col>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
                {t('common.search')}
              </Button>
              <Button onClick={handleReset} icon={<ClearOutlined />}>
                {t('common.reset')}
              </Button>
              <Button onClick={handleSaveSearch} icon={<SaveOutlined />}>
                {t('orders.saveSearch')}
              </Button>
              {onExport && (
                <Button 
                  onClick={() => onExport(form.getFieldsValue())} 
                  type="default"
                >
                  {t('orders.exportResults')}
                </Button>
              )}
            </Space>
          </Col>
        </Row>

        {/* Saved Searches */}
        {savedSearches.length > 0 && (
          <div className="mt-4">
            <h4>{t('orders.savedSearches')}</h4>
            <Space wrap>
              {savedSearches.map(search => (
                <Tag
                  key={search.id}
                  closable
                  onClose={() => handleDeleteSavedSearch(search.id)}
                  onClick={() => handleLoadSavedSearch(search)}
                  style={{ cursor: 'pointer' }}
                  icon={<HistoryOutlined />}
                >
                  {search.name}
                </Tag>
              ))}
            </Space>
          </div>
        )}
      </Form>
    </Card>
  );
};

export default OrderSearchPanel;