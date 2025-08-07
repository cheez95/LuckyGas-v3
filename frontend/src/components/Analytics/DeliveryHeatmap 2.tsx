import React from 'react';
import {
  Card,
  Typography,
  Row,
  Col,
  Tooltip,
} from 'antd';

interface DeliveryHeatmapProps {
  peakHour: number | null;
}

const { Title, Text } = Typography;

const DeliveryHeatmap: React.FC<DeliveryHeatmapProps> = ({ peakHour }) => {
  // Mock hourly data - in real app, this would come from API
  const generateHourlyData = () => {
    const data: { [key: string]: number[] } = {};
    const days = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
    
    days.forEach(day => {
      data[day] = Array.from({ length: 24 }, (_, hour) => {
        // Simulate realistic delivery patterns
        if (hour < 6 || hour > 20) return 0; // No deliveries at night
        if (hour === 9 || hour === 14) return 15 + Math.floor(Math.random() * 10); // Peak hours
        return 5 + Math.floor(Math.random() * 8);
      });
    });
    
    return data;
  };

  const hourlyData = generateHourlyData();
  const hours = Array.from({ length: 24 }, (_, i) => i);

  const getHeatColor = (value: number): string => {
    if (value === 0) return '#f5f5f5';
    if (value <= 5) return '#e3f2fd';
    if (value <= 10) return '#90caf9';
    if (value <= 15) return '#42a5f5';
    if (value <= 20) return '#1e88e5';
    return '#1565c0';
  };

  const formatHour = (hour: number): string => {
    return `${hour.toString().padStart(2, '0')}:00`;
  };

  return (
    <Card>
      <div style={{ padding: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>
          配送時段熱圖
        </Title>

        <div style={{ overflowX: 'auto' }}>
          <div style={{ minWidth: 800, marginTop: 16 }}>
            {/* Hour labels */}
            <Row gutter={0}>
              <Col flex="120px">
                <div style={{ height: 30 }} />
              </Col>
              {hours.map(hour => (
                <Col key={hour} flex="32px">
                  <div
                    style={{
                      height: 30,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {hour % 2 === 0 ? hour : ''}
                    </Text>
                  </div>
                </Col>
              ))}
            </Row>

            {/* Heatmap grid */}
            {Object.entries(hourlyData).map(([day, hourData]) => (
              <Row gutter={0} key={day}>
                <Col flex="120px">
                  <div
                    style={{
                      height: 40,
                      display: 'flex',
                      alignItems: 'center',
                      paddingLeft: 8,
                      paddingRight: 8
                    }}
                  >
                    <Text>{day}</Text>
                  </div>
                </Col>
                {hourData.map((value, hour) => (
                  <Col key={hour} flex="32px">
                    <Tooltip
                      title={`${day} ${formatHour(hour)}: ${value} 配送`}
                    >
                      <div
                        style={{
                          height: 40,
                          backgroundColor: getHeatColor(value),
                          border: '1px solid #fff',
                          cursor: 'pointer',
                          transition: 'transform 0.2s',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'scale(1.1)';
                          e.currentTarget.style.zIndex = '1';
                          e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'scale(1)';
                          e.currentTarget.style.zIndex = '0';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                      />
                    </Tooltip>
                  </Col>
                ))}
              </Row>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 16 }}>
          <Text type="secondary">
            配送密度：
          </Text>
          <div style={{ display: 'flex', gap: 8 }}>
            {[0, 5, 10, 15, 20].map(value => (
              <div key={value} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div
                  style={{
                    width: 20,
                    height: 20,
                    backgroundColor: getHeatColor(value),
                    border: '1px solid #ddd'
                  }}
                />
                <Text style={{ fontSize: 11 }}>{value}+</Text>
              </div>
            ))}
          </div>
        </div>

        {peakHour !== null && (
          <div style={{ marginTop: 16, padding: 16, backgroundColor: '#e6f7ff', borderRadius: 4 }}>
            <Text style={{ color: '#1890ff' }}>
              📊 今日尖峰時段：{formatHour(peakHour)} (根據即時數據)
            </Text>
          </div>
        )}
      </div>
    </Card>
  );
};

export default DeliveryHeatmap;