/**
 * Accessible navigation components with keyboard support and skip links
 */

import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, Breadcrumb } from 'antd';
import type { MenuProps } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useKeyboardNavigation, useSkipLinks, useAriaLive } from '../../hooks/useAccessibility';
import { KeyboardUtils, focusStyles } from '../../utils/accessibility';

/**
 * Skip navigation links for keyboard users
 */
export const SkipLinks: React.FC = () => {
  useSkipLinks();

  return (
    <div className="skip-links" style={{ position: 'absolute', top: '-40px', left: 0, zIndex: 9999 }}>
      <a
        href="#main-content"
        className="skip-link"
        style={{
          position: 'absolute',
          left: '-10000px',
          top: 'auto',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
        }}
        onFocus={(e) => {
          e.currentTarget.style.position = 'static';
          e.currentTarget.style.width = 'auto';
          e.currentTarget.style.height = 'auto';
          e.currentTarget.style.padding = '8px 16px';
          e.currentTarget.style.background = '#1890ff';
          e.currentTarget.style.color = '#fff';
          e.currentTarget.style.textDecoration = 'none';
          e.currentTarget.style.borderRadius = '4px';
        }}
        onBlur={(e) => {
          e.currentTarget.style.position = 'absolute';
          e.currentTarget.style.left = '-10000px';
          e.currentTarget.style.width = '1px';
          e.currentTarget.style.height = '1px';
        }}
      >
        跳至主要內容 (Alt+1)
      </a>
      
      <a
        href="#navigation"
        className="skip-link"
        style={{
          position: 'absolute',
          left: '-10000px',
          top: 'auto',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
        }}
        onFocus={(e) => {
          e.currentTarget.style.position = 'static';
          e.currentTarget.style.width = 'auto';
          e.currentTarget.style.height = 'auto';
          e.currentTarget.style.padding = '8px 16px';
          e.currentTarget.style.background = '#1890ff';
          e.currentTarget.style.color = '#fff';
          e.currentTarget.style.textDecoration = 'none';
          e.currentTarget.style.borderRadius = '4px';
        }}
        onBlur={(e) => {
          e.currentTarget.style.position = 'absolute';
          e.currentTarget.style.left = '-10000px';
          e.currentTarget.style.width = '1px';
          e.currentTarget.style.height = '1px';
        }}
      >
        跳至導航選單 (Alt+2)
      </a>
      
      <a
        href="#search"
        className="skip-link"
        style={{
          position: 'absolute',
          left: '-10000px',
          top: 'auto',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
        }}
        onFocus={(e) => {
          e.currentTarget.style.position = 'static';
          e.currentTarget.style.width = 'auto';
          e.currentTarget.style.height = 'auto';
          e.currentTarget.style.padding = '8px 16px';
          e.currentTarget.style.background = '#1890ff';
          e.currentTarget.style.color = '#fff';
          e.currentTarget.style.textDecoration = 'none';
          e.currentTarget.style.borderRadius = '4px';
        }}
        onBlur={(e) => {
          e.currentTarget.style.position = 'absolute';
          e.currentTarget.style.left = '-10000px';
          e.currentTarget.style.width = '1px';
          e.currentTarget.style.height = '1px';
        }}
      >
        跳至搜尋 (Alt+3)
      </a>
    </div>
  );
};

interface AccessibleMenuProps extends MenuProps {
  ariaLabel?: string;
  currentPath?: string;
}

/**
 * Accessible menu with keyboard navigation and ARIA attributes
 */
export const AccessibleMenu: React.FC<AccessibleMenuProps> = ({
  items,
  ariaLabel = '主導航選單',
  currentPath,
  ...props
}) => {
  const location = useLocation();
  const { announce, ariaLiveProps } = useAriaLive();
  const activeKey = currentPath || location.pathname;

  // Enhance menu items with ARIA attributes
  const enhancedItems = items?.map(item => ({
    ...item,
    'aria-current': item.key === activeKey ? 'page' : undefined,
  }));

  const handleSelect = ({ key }: { key: string }) => {
    const selectedItem = items?.find(item => item.key === key);
    if (selectedItem) {
      announce(`已選擇 ${selectedItem.label}`);
    }
  };

  return (
    <>
      <div {...ariaLiveProps} />
      <nav 
        id="navigation"
        aria-label={ariaLabel}
        role="navigation"
      >
        <Menu
          {...props}
          items={enhancedItems}
          selectedKeys={[activeKey]}
          onSelect={handleSelect}
          style={{
            ...props.style,
          }}
        />
      </nav>
    </>
  );
};

interface AccessibleBreadcrumbProps {
  items: Array<{
    title: string;
    path?: string;
    icon?: React.ReactNode;
  }>;
  ariaLabel?: string;
}

/**
 * Accessible breadcrumb navigation
 */
export const AccessibleBreadcrumb: React.FC<AccessibleBreadcrumbProps> = ({
  items,
  ariaLabel = '麵包屑導航',
}) => {
  const breadcrumbItems = items.map((item, index) => ({
    title: item.path ? (
      <Link 
        to={item.path}
        aria-current={index === items.length - 1 ? 'page' : undefined}
      >
        {item.icon}
        {item.title}
      </Link>
    ) : (
      <span aria-current={index === items.length - 1 ? 'page' : undefined}>
        {item.icon}
        {item.title}
      </span>
    ),
  }));

  return (
    <nav aria-label={ariaLabel}>
      <Breadcrumb 
        items={breadcrumbItems}
        separator="/"
      />
    </nav>
  );
};

interface TabItem {
  key: string;
  label: string;
  content: React.ReactNode;
  disabled?: boolean;
}

interface AccessibleTabsProps {
  items: TabItem[];
  defaultActiveKey?: string;
  onChange?: (key: string) => void;
  ariaLabel?: string;
}

/**
 * Accessible tabs with keyboard navigation
 */
export const AccessibleTabs: React.FC<AccessibleTabsProps> = ({
  items,
  defaultActiveKey,
  onChange,
  ariaLabel = '標籤選項',
}) => {
  const [activeKey, setActiveKey] = useState(defaultActiveKey || items[0]?.key);
  const { containerRef, keyboardNavigationProps } = useKeyboardNavigation({
    orientation: 'horizontal',
    onSelect: (index) => {
      const item = items[index];
      if (item && !item.disabled) {
        setActiveKey(item.key);
        onChange?.(item.key);
      }
    },
  });

  return (
    <div className="accessible-tabs">
      <div
        ref={containerRef as any}
        role="tablist"
        aria-label={ariaLabel}
        {...keyboardNavigationProps}
        style={{ display: 'flex', borderBottom: '1px solid #d9d9d9', marginBottom: '16px' }}
      >
        {items.map((item, index) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={activeKey === item.key}
            aria-controls={`tabpanel-${item.key}`}
            aria-disabled={item.disabled}
            disabled={item.disabled}
            tabIndex={activeKey === item.key ? 0 : -1}
            onClick={() => {
              if (!item.disabled) {
                setActiveKey(item.key);
                onChange?.(item.key);
              }
            }}
            style={{
              padding: '8px 16px',
              background: 'none',
              border: 'none',
              borderBottom: activeKey === item.key ? '2px solid #1890ff' : '2px solid transparent',
              color: item.disabled ? '#d9d9d9' : (activeKey === item.key ? '#1890ff' : '#000'),
              cursor: item.disabled ? 'not-allowed' : 'pointer',
              ...focusStyles.default,
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      
      {items.map(item => (
        <div
          key={item.key}
          id={`tabpanel-${item.key}`}
          role="tabpanel"
          aria-labelledby={`tab-${item.key}`}
          hidden={activeKey !== item.key}
          tabIndex={0}
        >
          {activeKey === item.key && item.content}
        </div>
      ))}
    </div>
  );
};

interface AccessiblePaginationProps {
  current: number;
  total: number;
  pageSize?: number;
  onChange: (page: number) => void;
  ariaLabel?: string;
}

/**
 * Accessible pagination with keyboard support
 */
export const AccessiblePagination: React.FC<AccessiblePaginationProps> = ({
  current,
  total,
  pageSize = 10,
  onChange,
  ariaLabel = '分頁導航',
}) => {
  const totalPages = Math.ceil(total / pageSize);
  const { announce, ariaLiveProps } = useAriaLive();

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== current) {
      onChange(page);
      announce(`已切換至第 ${page} 頁，共 ${totalPages} 頁`);
    }
  };

  const renderPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;
    
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    
    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(
        <button
          key={i}
          onClick={() => handlePageChange(i)}
          aria-label={`第 ${i} 頁`}
          aria-current={i === current ? 'page' : undefined}
          disabled={i === current}
          style={{
            margin: '0 4px',
            padding: '4px 8px',
            border: '1px solid #d9d9d9',
            background: i === current ? '#1890ff' : '#fff',
            color: i === current ? '#fff' : '#000',
            cursor: i === current ? 'default' : 'pointer',
            borderRadius: '4px',
            ...focusStyles.default,
          }}
        >
          {i}
        </button>
      );
    }
    
    return pages;
  };

  return (
    <>
      <div {...ariaLiveProps} />
      <nav 
        aria-label={ariaLabel}
        role="navigation"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '16px 0' }}
      >
        <button
          onClick={() => handlePageChange(current - 1)}
          disabled={current === 1}
          aria-label="上一頁"
          style={{
            margin: '0 4px',
            padding: '4px 8px',
            border: '1px solid #d9d9d9',
            background: '#fff',
            cursor: current === 1 ? 'not-allowed' : 'pointer',
            opacity: current === 1 ? 0.5 : 1,
            borderRadius: '4px',
            ...focusStyles.default,
          }}
        >
          上一頁
        </button>
        
        {renderPageNumbers()}
        
        <button
          onClick={() => handlePageChange(current + 1)}
          disabled={current === totalPages}
          aria-label="下一頁"
          style={{
            margin: '0 4px',
            padding: '4px 8px',
            border: '1px solid #d9d9d9',
            background: '#fff',
            cursor: current === totalPages ? 'not-allowed' : 'pointer',
            opacity: current === totalPages ? 0.5 : 1,
            borderRadius: '4px',
            ...focusStyles.default,
          }}
        >
          下一頁
        </button>
        
        <span style={{ marginLeft: '16px', color: '#8c8c8c' }}>
          第 {current} 頁，共 {totalPages} 頁
        </span>
      </nav>
    </>
  );
};

export default {
  SkipLinks,
  AccessibleMenu,
  AccessibleBreadcrumb,
  AccessibleTabs,
  AccessiblePagination,
};