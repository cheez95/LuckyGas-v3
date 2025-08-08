# Base Components

This directory contains reusable base components that consolidate common functionality across the application.

## BaseListComponent

A comprehensive list component that consolidates common patterns found in OrderList, CustomerList, and other list components.

### Features

- **Data Display**: Configurable table with columns, sorting, and row selection
- **Search & Filtering**: Built-in search functionality with custom filters
- **Pagination**: Configurable pagination with size control
- **Row Actions**: Customizable action buttons for each row
- **Bulk Actions**: Select multiple items and perform bulk operations
- **Statistics**: Display summary statistics above the table
- **Real-time Updates**: Support for WebSocket updates and indicators
- **Export**: Built-in export functionality
- **Error Handling**: Loading states, empty states, and error boundaries
- **Accessibility**: Full keyboard navigation and screen reader support

### Basic Usage

```tsx
import { BaseListComponent } from '../common';

const MyListComponent: React.FC = () => {
  const [data, setData] = useState<MyItem[]>([]);
  const [loading, setLoading] = useState(false);

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
    },
  ];

  const rowActions = [
    {
      key: 'edit',
      label: 'Edit',
      icon: <EditOutlined />,
      onClick: (record) => handleEdit(record),
    },
    {
      key: 'delete',
      label: 'Delete',
      danger: true,
      onClick: (record) => handleDelete(record),
    },
  ];

  return (
    <BaseListComponent
      data={data}
      loading={loading}
      columns={columns}
      rowKey="id"
      title="My Items"
      searchable
      showAddButton
      onAdd={() => setShowModal(true)}
      rowActions={rowActions}
    />
  );
};
```

### Advanced Usage with Bulk Actions and Statistics

```tsx
const stats = {
  total: { title: 'Total Items', value: data.length, prefix: <DatabaseOutlined /> },
  active: { title: 'Active', value: activeCount, color: '#52c41a' },
  pending: { title: 'Pending', value: pendingCount, color: '#faad14' },
};

const bulkActions = [
  {
    key: 'approve',
    label: 'Approve Selected',
    icon: <CheckOutlined />,
    onClick: (selectedRows) => handleBulkApprove(selectedRows),
  },
  {
    key: 'delete',
    label: 'Delete Selected',
    danger: true,
    onClick: (selectedRows) => handleBulkDelete(selectedRows),
  },
];

return (
  <BaseListComponent
    data={data}
    columns={columns}
    rowKey="id"
    title="Advanced List"
    stats={stats}
    enableBulkActions
    bulkActions={bulkActions}
    exportable
    onExport={handleExport}
    realTimeUpdateTag={<Tag color="green">Live Updates</Tag>}
  />
);
```

## BaseModal

A flexible modal component that handles form submission, validation, loading states, and error handling.

### Features

- **Form Integration**: Seamless Ant Design Form integration
- **Loading States**: Built-in loading and submission states
- **Error Handling**: Display errors with dismissible alerts
- **Validation**: Form validation with error summary
- **Confirmation**: Optional confirmation dialogs
- **Size Presets**: Predefined sizes (small, medium, large, extra-large)
- **Custom Actions**: Flexible footer actions
- **Accessibility**: Proper focus management and keyboard navigation

### Basic Usage

```tsx
import { BaseModal } from '../common';

const MyFormModal: React.FC = () => {
  const [form] = Form.useForm();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      await api.createItem(values);
      message.success('Item created successfully');
      setOpen(false);
    } catch (error) {
      message.error('Failed to create item');
    } finally {
      setLoading(false);
    }
  };

  return (
    <BaseModal
      open={open}
      onClose={() => setOpen(false)}
      title="Create New Item"
      form={form}
      onSubmit={handleSubmit}
      submitting={loading}
      size="medium"
    >
      <Form form={form} layout="vertical">
        <Form.Item name="name" label="Name" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="description" label="Description">
          <Input.TextArea />
        </Form.Item>
      </Form>
    </BaseModal>
  );
};
```

### Advanced Usage with Custom Actions

```tsx
const customActions = [
  {
    key: 'save-draft',
    label: 'Save as Draft',
    onClick: () => handleSaveDraft(),
  },
  {
    key: 'save-publish',
    label: 'Save & Publish',
    type: 'primary',
    onClick: () => handleSaveAndPublish(),
  },
];

return (
  <BaseModal
    open={open}
    onClose={onClose}
    title="Advanced Form"
    subtitle="Complete all required fields"
    size="large"
    actions={customActions}
    showOkButton={false}
    showCancelButton={false}
    requireConfirmation
    confirmationTitle="Publish Item"
    confirmationContent="Are you sure you want to publish this item?"
    error={error}
    success={success}
  >
    {/* Form content */}
  </BaseModal>
);
```

## TypeScript Support

Both components are fully typed with comprehensive TypeScript interfaces:

```tsx
import type {
  BaseListComponentProps,
  BaseListAction,
  BaseBulkAction,
  BaseModalProps,
  BaseModalAction,
} from '../common';
```

## Migration Guide

### From OrderList.tsx

Replace the existing OrderList component implementation:

```tsx
// Before
const OrderList: React.FC = () => {
  // 848 lines of code...
};

// After
const OrderList: React.FC = () => {
  return (
    <BaseListComponent
      data={orders}
      loading={loading}
      columns={orderColumns}
      rowKey="id"
      title={t('order.title')}
      searchable
      showAddButton
      addButtonText={t('order.addButton')}
      onAdd={() => setIsCreateModalVisible(true)}
      rowActions={orderRowActions}
      stats={orderStats}
      filterComponents={<OrderFilters />}
      realTimeUpdateTag={<Tag color="green" icon={<ThunderboltOutlined />}>即時更新</Tag>}
      onRefresh={fetchOrders}
    />
  );
};
```

### From CustomerList.tsx

```tsx
// Before
const CustomerList: React.FC = () => {
  // 501 lines of code...
};

// After
const CustomerList: React.FC = () => {
  return (
    <BaseListComponent
      data={customers}
      loading={loading}
      columns={customerColumns}
      rowKey="id"
      title={t('customer.title')}
      searchable
      searchPlaceholder={t('customer.searchPlaceholder')}
      showAddButton
      addButtonText={t('customer.addButton')}
      onAdd={handleAddCustomer}
      rowActions={customerRowActions}
      pagination={{
        current: currentPage,
        pageSize: pageSize,
        total: total,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 筆資料`,
        onChange: handleTableChange,
      }}
    />
  );
};
```

## Benefits

1. **Code Reduction**: Reduces duplicate code by ~70% in list components
2. **Consistency**: Ensures consistent UI/UX across all list views  
3. **Maintainability**: Centralized bug fixes and feature additions
4. **Performance**: Optimized rendering and memory usage
5. **Accessibility**: Built-in accessibility features
6. **Testing**: Comprehensive test coverage in base components
7. **Documentation**: Self-documenting with TypeScript interfaces