import React, { useEffect, useState } from 'react';
import { Card, Button, Space, Alert, Divider, Table, Typography } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { orderService } from '../services/order.service';
import { routeService } from '../services/route.service';
import { driverService } from '../services/driver.service';
import { customerService } from '../services/customer.service';
import { toArray, safeMap, SafeArray } from '../utils/dataHelpers';

const { Title, Text, Paragraph } = Typography;

interface TestResult {
  endpoint: string;
  status: 'success' | 'error' | 'pending';
  responseType: string;
  dataStructure: string;
  arrayField?: string;
  error?: string;
  rawResponse?: any;
}

const TestDataStructures: React.FC = () => {
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const testEndpoint = async (
    name: string,
    testFn: () => Promise<any>
  ): Promise<TestResult> => {
    try {
      console.log(`[TEST] Testing endpoint: ${name}`);
      const response = await testFn();
      
      console.log(`[TEST] ${name} response:`, response);
      console.log(`[TEST] ${name} type:`, typeof response);
      
      // Analyze the response structure
      let responseType = typeof response;
      let dataStructure = 'unknown';
      let arrayField: string | undefined;
      
      if (Array.isArray(response)) {
        dataStructure = 'array';
      } else if (response && typeof response === 'object') {
        const keys = Object.keys(response);
        dataStructure = `object with keys: [${keys.join(', ')}]`;
        
        // Find array fields
        for (const key of keys) {
          if (Array.isArray(response[key])) {
            arrayField = key;
            break;
          }
        }
      }
      
      return {
        endpoint: name,
        status: 'success',
        responseType,
        dataStructure,
        arrayField,
        rawResponse: response
      };
    } catch (error: any) {
      console.error(`[TEST] ${name} error:`, error);
      return {
        endpoint: name,
        status: 'error',
        responseType: 'error',
        dataStructure: 'N/A',
        error: error.message || 'Unknown error'
      };
    }
  };

  const runAllTests = async () => {
    setIsRunning(true);
    setTestResults([]);
    
    const tests = [
      // Order Service
      {
        name: 'orderService.searchOrders',
        fn: () => orderService.searchOrders({
          dateFrom: new Date().toISOString().split('T')[0],
          dateTo: new Date().toISOString().split('T')[0],
          status: ['pending', 'confirmed']
        })
      },
      {
        name: 'orderService.getOrders',
        fn: () => orderService.getOrders({})
      },
      
      // Driver Service
      {
        name: 'driverService.getDrivers',
        fn: () => driverService.getDrivers()
      },
      {
        name: 'driverService.getAvailableDrivers',
        fn: () => driverService.getAvailableDrivers(new Date().toISOString().split('T')[0])
      },
      
      // Route Service
      {
        name: 'routeService.getRoutes',
        fn: () => routeService.getRoutes({
          date: new Date().toISOString().split('T')[0]
        })
      },
      {
        name: 'routeService.optimizeRoute',
        fn: () => routeService.optimizeRoute({
          date: new Date().toISOString().split('T')[0],
          orderIds: []
        })
      },
      
      // Customer Service
      {
        name: 'customerService.getCustomers',
        fn: () => customerService.getCustomers({})
      },
      {
        name: 'customerService.searchCustomers',
        fn: () => customerService.searchCustomers('')
      }
    ];
    
    const results: TestResult[] = [];
    
    for (const test of tests) {
      const result = await testEndpoint(test.name, test.fn);
      results.push(result);
      setTestResults([...results]);
      
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setIsRunning(false);
  };

  const testSafeArrayHandling = () => {
    console.log('=== Testing SafeArray Utils ===');
    
    const testCases = [
      { input: null, expected: [] },
      { input: undefined, expected: [] },
      { input: [], expected: [] },
      { input: [1, 2, 3], expected: [1, 2, 3] },
      { input: { data: [1, 2, 3] }, expected: [1, 2, 3] },
      { input: { items: [1, 2, 3] }, expected: [1, 2, 3] },
      { input: { results: [1, 2, 3] }, expected: [1, 2, 3] },
      { input: { drivers: [1, 2, 3] }, expected: [1, 2, 3] },
      { input: { orders: [1, 2, 3] }, expected: [1, 2, 3] },
      { input: { randomKey: [1, 2, 3] }, expected: [1, 2, 3] },
      { input: { id: 1, name: 'test' }, expected: [{ id: 1, name: 'test' }] },
      { input: 'string', expected: [] },
      { input: 123, expected: [] }
    ];
    
    testCases.forEach((testCase, index) => {
      const result = toArray(testCase.input);
      const passed = JSON.stringify(result) === JSON.stringify(testCase.expected);
      console.log(
        `Test ${index + 1}: ${passed ? '✅' : '❌'}`,
        `Input:`, testCase.input,
        `Expected:`, testCase.expected,
        `Got:`, result
      );
    });
  };

  useEffect(() => {
    // Run SafeArray tests on mount
    testSafeArrayHandling();
  }, []);

  const columns = [
    {
      title: 'Endpoint',
      dataIndex: 'endpoint',
      key: 'endpoint',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        status === 'success' ? 
          <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
        status === 'error' ?
          <CloseCircleOutlined style={{ color: '#f5222d' }} /> :
          <span>-</span>
      )
    },
    {
      title: 'Response Type',
      dataIndex: 'responseType',
      key: 'responseType',
    },
    {
      title: 'Data Structure',
      dataIndex: 'dataStructure',
      key: 'dataStructure',
    },
    {
      title: 'Array Field',
      dataIndex: 'arrayField',
      key: 'arrayField',
      render: (field: string) => field || '-'
    },
    {
      title: 'Error',
      dataIndex: 'error',
      key: 'error',
      render: (error: string) => error ? <Text type="danger">{error}</Text> : '-'
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={2}>Data Structure Test Page</Title>
        <Paragraph>
          This page tests all API endpoints to identify their response structures
          and helps debug "map is not a function" errors.
        </Paragraph>
        
        <Alert
          message="Debug Mode"
          description="Open the browser console to see detailed logs of each API response."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <Space style={{ marginBottom: 16 }}>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={runAllTests}
            loading={isRunning}
          >
            Run All Tests
          </Button>
          
          <Button
            onClick={() => {
              console.clear();
              testSafeArrayHandling();
            }}
          >
            Test SafeArray Utils
          </Button>
          
          <Button
            onClick={() => {
              console.log('Current test results:', testResults);
              testResults.forEach(result => {
                if (result.rawResponse) {
                  console.log(`\n${result.endpoint} raw response:`, result.rawResponse);
                }
              });
            }}
          >
            Log All Responses
          </Button>
        </Space>
        
        <Divider />
        
        <Title level={4}>Test Results</Title>
        <Table
          columns={columns}
          dataSource={testResults}
          rowKey="endpoint"
          pagination={false}
        />
        
        {testResults.length > 0 && (
          <>
            <Divider />
            <Title level={4}>Summary</Title>
            <Space direction="vertical">
              <Text>
                Total Tests: {testResults.length}
              </Text>
              <Text type="success">
                Successful: {testResults.filter(r => r.status === 'success').length}
              </Text>
              <Text type="danger">
                Failed: {testResults.filter(r => r.status === 'error').length}
              </Text>
            </Space>
            
            <Divider />
            <Title level={4}>Recommendations</Title>
            <ul>
              {testResults.filter(r => r.status === 'success' && !r.arrayField && r.dataStructure !== 'array').map(r => (
                <li key={r.endpoint}>
                  <Text type="warning">
                    {r.endpoint} returns {r.dataStructure} - needs array extraction logic
                  </Text>
                </li>
              ))}
              {testResults.filter(r => r.status === 'success' && r.arrayField).map(r => (
                <li key={r.endpoint}>
                  <Text type="success">
                    {r.endpoint} has array in field "{r.arrayField}" - toArray() will handle this
                  </Text>
                </li>
              ))}
              {testResults.filter(r => r.status === 'success' && r.dataStructure === 'array').map(r => (
                <li key={r.endpoint}>
                  <Text type="success">
                    {r.endpoint} returns array directly - no extraction needed
                  </Text>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>
    </div>
  );
};

export default TestDataStructures;