import React, { useState, useEffect, ReactNode } from 'react';
import {
  Table,
  Card,
  Input,
  Button,
  Space,
  Typography,
  Tag,
  message,
  Select,
  DatePicker,
  Row,
  Col,
  Statistic,
  Spin,
  Empty,
  Alert,
} from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  ReloadOutlined,
  DownloadOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import type { ColumnsType, TableProps } from 'antd/es/table';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';

const { Title } = Typography;
const { Search } = Input;
const { RangePicker } = DatePicker;

export interface BaseListFilter {
  [key: string]: any;
}

export interface BaseListStats {
  [key: string]: {
    title: string;
    value: number | string;
    prefix?: ReactNode;
    suffix?: string;
    color?: string;
  };
}

export interface BaseListAction<T = any> {
  key: string;
  label: string;
  icon?: ReactNode;
  type?: 'primary' | 'default' | 'dashed' | 'text' | 'link';
  danger?: boolean;
  disabled?: (record: T) => boolean;
  visible?: (record: T) => boolean;
  onClick: (record: T) => void;
}

export interface BaseBulkAction<T = any> {
  key: string;
  label: string;
  icon?: ReactNode;
  type?: 'primary' | 'default' | 'dashed';
  danger?: boolean;
  disabled?: (selectedRows: T[]) => boolean;
  onClick: (selectedRows: T[], selectedRowKeys: React.Key[]) => void;
}

export interface BaseListComponentProps<T = any> {
  // Data
  data: T[];
  loading?: boolean;
  total?: number;
  
  // Table configuration
  columns: ColumnsType<T>;
  rowKey: string | ((record: T) => string);
  scroll?: { x?: number; y?: number };
  
  // Title and actions
  title: string;
  showAddButton?: boolean;
  addButtonText?: string;
  onAdd?: () => void;
  extraActions?: ReactNode;
  
  // Search and filters
  searchable?: boolean;
  searchPlaceholder?: string;
  onSearch?: (value: string) => void;
  filters?: BaseListFilter;
  onFiltersChange?: (filters: BaseListFilter) => void;
  filterComponents?: ReactNode;
  
  // Pagination
  pagination?: false | {
    current?: number;
    pageSize?: number;
    total?: number;
    showSizeChanger?: boolean;
    showTotal?: boolean | ((total: number, range: [number, number]) => ReactNode);
    onChange?: (page: number, pageSize: number) => void;
  };
  
  // Row actions
  rowActions?: BaseListAction<T>[];
  
  // Bulk actions
  enableBulkActions?: boolean;
  bulkActions?: BaseBulkAction<T>[];
  selectedRowKeys?: React.Key[];
  onSelectionChange?: (selectedRowKeys: React.Key[], selectedRows: T[]) => void;
  
  // Statistics
  stats?: BaseListStats;
  
  // Real-time updates
  realTimeUpdateTag?: ReactNode;
  
  // Export functionality
  exportable?: boolean;
  onExport?: () => void;
  
  // Custom renderers
  emptyText?: ReactNode;
  errorComponent?: ReactNode;
  
  // Additional table props
  tableProps?: Omit<TableProps<T>, 'columns' | 'dataSource' | 'rowKey' | 'loading' | 'scroll' | 'pagination'>;
  
  // Callbacks
  onRefresh?: () => void;
  onRowClick?: (record: T) => void;
  
  // Error handling
  error?: string | null;
  onRetry?: () => void;
}

const BaseListComponent = <T extends Record<string, any>>({
  data,
  loading = false,
  total = 0,
  columns,
  rowKey,
  scroll = { x: 1500 },
  title,
  showAddButton = false,
  addButtonText = 'Add',
  onAdd,
  extraActions,
  searchable = false,
  searchPlaceholder = 'Search...',
  onSearch,
  filters,
  onFiltersChange,
  filterComponents,
  pagination = {
    current: 1,
    pageSize: 10,
    showSizeChanger: true,
    showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} items`,
  },
  rowActions = [],
  enableBulkActions = false,
  bulkActions = [],
  selectedRowKeys = [],
  onSelectionChange,
  stats,
  realTimeUpdateTag,
  exportable = false,
  onExport,
  emptyText,
  errorComponent,
  tableProps = {},
  onRefresh,
  onRowClick,
  error,
  onRetry,
}: BaseListComponentProps<T>): React.ReactElement => {
  const { t } = useTranslation();
  const [searchText, setSearchText] = useState('');
  const [internalSelectedRowKeys, setInternalSelectedRowKeys] = useState<React.Key[]>(selectedRowKeys);

  // Update internal selected row keys when prop changes
  useEffect(() => {
    setInternalSelectedRowKeys(selectedRowKeys);
  }, [selectedRowKeys]);

  // Handle search
  const handleSearch = (value: string) => {
    setSearchText(value);
    onSearch?.(value);
  };

  // Handle refresh
  const handleRefresh = () => {
    onRefresh?.();
  };

  // Handle row selection
  const handleSelectionChange = (newSelectedRowKeys: React.Key[], selectedRows: T[]) => {
    setInternalSelectedRowKeys(newSelectedRowKeys);
    onSelectionChange?.(newSelectedRowKeys, selectedRows);
  };

  // Add action column if row actions are provided
  const enhancedColumns: ColumnsType<T> = rowActions.length > 0 
    ? [
        ...columns,
        {
          title: t('app.actions', 'Actions'),
          key: 'actions',
          fixed: 'right',
          width: Math.max(rowActions.length * 50, 120),
          render: (_, record) => (
            <Space size="small">
              {rowActions
                .filter(action => action.visible ? action.visible(record) : true)
                .map(action => (
                  <Button
                    key={action.key}
                    size="small"
                    type={action.type || 'text'}
                    danger={action.danger}
                    disabled={action.disabled ? action.disabled(record) : false}
                    icon={action.icon}
                    onClick={() => action.onClick(record)}
                  >
                    {action.label}
                  </Button>
                ))}
            </Space>
          ),
        },
      ]
    : columns;

  // Row selection configuration
  const rowSelection = enableBulkActions ? {
    selectedRowKeys: internalSelectedRowKeys,
    onChange: handleSelectionChange,
    getCheckboxProps: (record: T) => ({
      disabled: false, // Can be customized based on record
    }),
  } : undefined;

  // Render statistics
  const renderStats = () => {
    if (!stats || Object.keys(stats).length === 0) return null;

    return (
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {Object.entries(stats).map(([key, stat]) => (
          <Col span={24 / Object.keys(stats).length} key={key}>
            <Card>
              <Statistic
                title={stat.title}
                value={stat.value}
                prefix={stat.prefix}
                suffix={stat.suffix}
                valueStyle={{ color: stat.color }}
              />
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  // Render bulk actions
  const renderBulkActions = () => {
    if (!enableBulkActions || bulkActions.length === 0 || internalSelectedRowKeys.length === 0) return null;

    const selectedRows = data.filter(item => internalSelectedRowKeys.includes(
      typeof rowKey === 'string' ? item[rowKey] : rowKey(item)
    ));

    return (
      <div style={{ marginBottom: 16, padding: 12, backgroundColor: '#f0f8ff', borderRadius: 4 }}>
        <Space>
          <span>Selected {internalSelectedRowKeys.length} items:</span>
          {bulkActions
            .filter(action => !action.disabled || !action.disabled(selectedRows))
            .map(action => (
              <Button
                key={action.key}
                type={action.type || 'default'}
                danger={action.danger}
                icon={action.icon}
                onClick={() => action.onClick(selectedRows, internalSelectedRowKeys)}
              >
                {action.label}
              </Button>
            ))}
          <Button
            size="small"
            onClick={() => handleSelectionChange([], [])}
          >
            Clear Selection
          </Button>
        </Space>
      </div>
    );
  };

  // Render error state
  if (error && errorComponent) {
    return <>{errorComponent}</>;
  }

  if (error) {
    return (
      <Card>
        <Alert
          message="Error Loading Data"
          description={error}
          type="error"
          action={
            onRetry ? (
              <Button size="small" danger onClick={onRetry}>
                Retry
              </Button>
            ) : undefined
          }
        />
      </Card>
    );
  }

  return (
    <div className="base-list-component">
      {/* Statistics */}
      {renderStats()}

      {/* Main Card */}
      <Card
        title={
          <Space>
            <Title level={3} style={{ margin: 0 }}>{title}</Title>
            {realTimeUpdateTag}
          </Space>
        }
        extra={
          <Space>
            {searchable && (
              <Search
                placeholder={searchPlaceholder}
                allowClear
                enterButton={<SearchOutlined />}
                size="middle"
                onSearch={handleSearch}
                style={{ width: 250 }}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
            )}
            {exportable && onExport && (
              <Button icon={<DownloadOutlined />} onClick={onExport}>
                Export
              </Button>
            )}
            {showAddButton && onAdd && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={onAdd}
              >
                {addButtonText}
              </Button>
            )}
            {onRefresh && (
              <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                Refresh
              </Button>
            )}
            {extraActions}
          </Space>
        }
      >
        {/* Filter Components */}
        {filterComponents && (
          <div style={{ marginBottom: 16 }}>
            {filterComponents}
          </div>
        )}

        {/* Bulk Actions */}
        {renderBulkActions()}

        {/* Table */}
        <Table
          columns={enhancedColumns}
          dataSource={data}
          rowKey={rowKey}
          loading={loading}
          scroll={scroll}
          pagination={pagination}
          rowSelection={rowSelection}
          onRow={onRowClick ? (record) => ({
            onClick: () => onRowClick(record),
            style: { cursor: onRowClick ? 'pointer' : 'default' }
          }) : undefined}
          locale={{
            emptyText: emptyText || (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={<span>No data available</span>}
              />
            ),
          }}
          {...tableProps}
        />
      </Card>
    </div>
  );
};

export default BaseListComponent;