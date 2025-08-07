/**
 * Accessibility checker component for development testing
 */

import React, { useState, useEffect } from 'react';
import { Card, Button, Tag, Alert, Collapse, Space, Switch, Tooltip } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { getContrastRatio, meetsWCAG, validateTouchTarget, FocusManager } from '../../utils/accessibility';

const { Panel } = Collapse;

interface AccessibilityIssue {
  type: 'error' | 'warning' | 'info';
  category: string;
  element?: HTMLElement;
  message: string;
  recommendation: string;
  wcagCriteria: string;
}

/**
 * Accessibility checker for development environment
 * Provides real-time accessibility validation and recommendations
 */
export const AccessibilityChecker: React.FC = () => {
  const [isEnabled, setIsEnabled] = useState(process.env.NODE_ENV === 'development');
  const [issues, setIssues] = useState<AccessibilityIssue[]>([]);
  const [isChecking, setIsChecking] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);

  const runAccessibilityCheck = () => {
    setIsChecking(true);
    const newIssues: AccessibilityIssue[] = [];

    // Check images for alt text
    document.querySelectorAll('img').forEach(img => {
      if (!img.alt && !img.getAttribute('role')) {
        newIssues.push({
          type: 'error',
          category: '圖片',
          element: img,
          message: '圖片缺少替代文字',
          recommendation: '為圖片添加 alt 屬性描述圖片內容',
          wcagCriteria: 'WCAG 1.1.1 Non-text Content',
        });
      }
    });

    // Check form inputs for labels
    document.querySelectorAll('input, select, textarea').forEach(input => {
      const htmlInput = input as HTMLInputElement;
      if (!htmlInput.labels?.length && !input.getAttribute('aria-label') && !input.getAttribute('aria-labelledby')) {
        newIssues.push({
          type: 'error',
          category: '表單',
          element: htmlInput,
          message: `表單元素缺少標籤: ${htmlInput.type || 'input'}`,
          recommendation: '為表單元素添加 <label> 或 aria-label',
          wcagCriteria: 'WCAG 3.3.2 Labels or Instructions',
        });
      }
    });

    // Check heading hierarchy
    const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
    let previousLevel = 0;
    headings.forEach(heading => {
      const level = parseInt(heading.tagName[1]);
      if (previousLevel > 0 && level > previousLevel + 1) {
        newIssues.push({
          type: 'warning',
          category: '標題',
          element: heading,
          message: `標題層級跳躍: 從 H${previousLevel} 跳到 H${level}`,
          recommendation: '保持標題層級連續性',
          wcagCriteria: 'WCAG 1.3.1 Info and Relationships',
        });
      }
      previousLevel = level;
    });

    // Check color contrast
    const textElements = document.querySelectorAll('p, span, div, a, button, li, td, th');
    textElements.forEach(element => {
      const htmlElement = element as HTMLElement;
      const computedStyle = window.getComputedStyle(htmlElement);
      const color = computedStyle.color;
      const backgroundColor = computedStyle.backgroundColor;
      
      if (color && backgroundColor && backgroundColor !== 'rgba(0, 0, 0, 0)') {
        const ratio = getContrastRatio(color, backgroundColor);
        const fontSize = parseFloat(computedStyle.fontSize);
        const isLargeText = fontSize >= 18 || (fontSize >= 14 && computedStyle.fontWeight === 'bold');
        
        if (!meetsWCAG(color, backgroundColor, 'AA', isLargeText)) {
          newIssues.push({
            type: 'error',
            category: '顏色對比',
            element: htmlElement,
            message: `文字對比度不足: ${ratio.toFixed(2)}:1 (需要 ${isLargeText ? '3:1' : '4.5:1'})`,
            recommendation: '調整文字或背景顏色以提高對比度',
            wcagCriteria: 'WCAG 1.4.3 Contrast (Minimum)',
          });
        }
      }
    });

    // Check touch targets
    document.querySelectorAll('button, a, input[type="checkbox"], input[type="radio"]').forEach(element => {
      const htmlElement = element as HTMLElement;
      if (!validateTouchTarget(htmlElement)) {
        const rect = htmlElement.getBoundingClientRect();
        newIssues.push({
          type: 'warning',
          category: '觸控目標',
          element: htmlElement,
          message: `觸控目標太小: ${Math.round(rect.width)}x${Math.round(rect.height)}px (需要至少 44x44px)`,
          recommendation: '增加元素大小或填充以達到最小觸控目標要求',
          wcagCriteria: 'WCAG 2.5.5 Target Size',
        });
      }
    });

    // Check keyboard navigation
    const focusableElements = FocusManager.getFocusableElements(document.body);
    focusableElements.forEach(element => {
      if (!element.getAttribute('tabindex') && element.tagName !== 'A' && element.tagName !== 'BUTTON' && element.tagName !== 'INPUT' && element.tagName !== 'SELECT' && element.tagName !== 'TEXTAREA') {
        newIssues.push({
          type: 'info',
          category: '鍵盤導航',
          element: element,
          message: '可互動元素可能需要 tabindex',
          recommendation: '確保所有可互動元素都可以通過鍵盤訪問',
          wcagCriteria: 'WCAG 2.1.1 Keyboard',
        });
      }
    });

    // Check ARIA attributes
    document.querySelectorAll('[aria-hidden="true"]').forEach(element => {
      if (element.querySelector('a, button, input, select, textarea')) {
        newIssues.push({
          type: 'error',
          category: 'ARIA',
          element: element as HTMLElement,
          message: 'aria-hidden 元素包含可互動內容',
          recommendation: '不要在包含可互動元素的容器上使用 aria-hidden="true"',
          wcagCriteria: 'WCAG 4.1.2 Name, Role, Value',
        });
      }
    });

    // Check for missing lang attribute
    if (!document.documentElement.lang) {
      newIssues.push({
        type: 'error',
        category: '語言',
        message: 'HTML 缺少 lang 屬性',
        recommendation: '在 <html> 標籤添加 lang="zh-TW"',
        wcagCriteria: 'WCAG 3.1.1 Language of Page',
      });
    }

    // Check for duplicate IDs
    const ids = new Map<string, HTMLElement[]>();
    document.querySelectorAll('[id]').forEach(element => {
      const id = element.id;
      if (!ids.has(id)) {
        ids.set(id, []);
      }
      ids.get(id)!.push(element as HTMLElement);
    });
    
    ids.forEach((elements, id) => {
      if (elements.length > 1) {
        newIssues.push({
          type: 'error',
          category: 'HTML',
          message: `重複的 ID: "${id}" 出現 ${elements.length} 次`,
          recommendation: '確保每個 ID 在頁面中是唯一的',
          wcagCriteria: 'WCAG 4.1.1 Parsing',
        });
      }
    });

    setIssues(newIssues);
    setIsChecking(false);
  };

  useEffect(() => {
    if (isEnabled) {
      // Run initial check after page load
      const timer = setTimeout(runAccessibilityCheck, 1000);
      return () => clearTimeout(timer);
    }
  }, [isEnabled]);

  const highlightElement = (element?: HTMLElement) => {
    if (!element) return;
    
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    element.style.outline = '3px solid red';
    element.style.outlineOffset = '2px';
    
    setTimeout(() => {
      element.style.outline = '';
      element.style.outlineOffset = '';
    }, 3000);
  };

  const getIssueIcon = (type: AccessibilityIssue['type']) => {
    switch (type) {
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'info':
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
    }
  };

  const getIssueColor = (type: AccessibilityIssue['type']) => {
    switch (type) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'processing';
    }
  };

  if (!isEnabled) {
    return null;
  }

  const errorCount = issues.filter(i => i.type === 'error').length;
  const warningCount = issues.filter(i => i.type === 'warning').length;
  const infoCount = issues.filter(i => i.type === 'info').length;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        zIndex: 9999,
        maxWidth: 400,
      }}
    >
      <Card
        title={
          <Space>
            <span>無障礙檢查器</span>
            <Switch
              checked={isEnabled}
              onChange={setIsEnabled}
              checkedChildren="開"
              unCheckedChildren="關"
            />
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="重新檢查">
              <Button
                type="primary"
                size="small"
                onClick={runAccessibilityCheck}
                loading={isChecking}
              >
                檢查
              </Button>
            </Tooltip>
            <Tooltip title="顯示視覺標記">
              <Button
                size="small"
                onClick={() => setShowOverlay(!showOverlay)}
              >
                標記
              </Button>
            </Tooltip>
          </Space>
        }
        style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
      >
        {issues.length === 0 ? (
          <Alert
            message="未發現無障礙問題"
            description="頁面符合 WCAG 2.1 AA 標準"
            type="success"
            icon={<CheckCircleOutlined />}
            showIcon
          />
        ) : (
          <>
            <Space style={{ marginBottom: 16 }}>
              {errorCount > 0 && (
                <Tag color="error">{errorCount} 個錯誤</Tag>
              )}
              {warningCount > 0 && (
                <Tag color="warning">{warningCount} 個警告</Tag>
              )}
              {infoCount > 0 && (
                <Tag color="processing">{infoCount} 個提示</Tag>
              )}
            </Space>
            
            <Collapse 
              accordion
              size="small"
              style={{ maxHeight: 400, overflowY: 'auto' }}
            >
              {issues.map((issue, index) => (
                <Panel
                  key={index}
                  header={
                    <Space>
                      {getIssueIcon(issue.type)}
                      <span>{issue.message}</span>
                    </Space>
                  }
                  extra={
                    <Tag color={getIssueColor(issue.type)}>
                      {issue.category}
                    </Tag>
                  }
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <strong>建議：</strong>
                      <div>{issue.recommendation}</div>
                    </div>
                    <div>
                      <strong>WCAG 標準：</strong>
                      <div>{issue.wcagCriteria}</div>
                    </div>
                    {issue.element && (
                      <Button
                        size="small"
                        onClick={() => highlightElement(issue.element)}
                      >
                        定位元素
                      </Button>
                    )}
                  </Space>
                </Panel>
              ))}
            </Collapse>
          </>
        )}
      </Card>
    </div>
  );
};

export default AccessibilityChecker;