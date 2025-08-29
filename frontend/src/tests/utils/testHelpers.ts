/**
 * General test helper utilities
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Wait helpers
export const waitForElementToBeRemoved = async (element: HTMLElement | null, timeout = 5000) => {
  if (!element) return;
  await waitFor(() => {
    expect(element).not.toBeInTheDocument();
  }, { timeout });
};

export const waitForLoadingToFinish = async () => {
  const loadingElements = screen.queryAllByText(/loading|載入中/i);
  await Promise.all(loadingElements.map(el => waitForElementToBeRemoved(el)));
};

// Form helpers
export const fillForm = async (formData: Record<string, string | number | boolean>) => {
  const user = userEvent.setup();
  
  for (const [name, value] of Object.entries(formData)) {
    const element = screen.getByLabelText(new RegExp(name, 'i'));
    
    if (element.tagName === 'INPUT') {
      const input = element as HTMLInputElement;
      if (input.type === 'checkbox') {
        if (value !== input.checked) {
          await user.click(input);
        }
      } else {
        await user.clear(input);
        await user.type(input, String(value));
      }
    } else if (element.tagName === 'SELECT') {
      await user.selectOptions(element, String(value));
    } else if (element.tagName === 'TEXTAREA') {
      await user.clear(element);
      await user.type(element, String(value));
    }
  }
};

export const submitForm = async (buttonText: string | RegExp = /submit|提交/i) => {
  const user = userEvent.setup();
  const submitButton = screen.getByRole('button', { name: buttonText });
  await user.click(submitButton);
};

// Table helpers
export const getTableRows = (container?: HTMLElement) => {
  const table = container ? within(container).getByRole('table') : screen.getByRole('table');
  return within(table).getAllByRole('row').slice(1); // Skip header row
};

export const getTableCellValue = (row: HTMLElement, columnIndex: number): string => {
  const cells = within(row).getAllByRole('cell');
  return cells[columnIndex]?.textContent || '';
};

export const findRowByText = (text: string | RegExp, container?: HTMLElement): HTMLElement | null => {
  const rows = getTableRows(container);
  return rows.find(row => within(row).queryByText(text) !== null) || null;
};

// Select helpers (for Ant Design Select)
export const selectOption = async (labelText: string | RegExp, optionText: string) => {
  const user = userEvent.setup();
  
  // Find the select by label
  const label = screen.getByText(labelText);
  const selectContainer = label.closest('.ant-form-item')?.querySelector('.ant-select');
  if (!selectContainer) throw new Error('Select not found');
  
  // Click to open dropdown
  await user.click(selectContainer);
  
  // Wait for dropdown to appear
  await waitFor(() => {
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });
  
  // Click the option
  const option = screen.getByTitle(optionText);
  await user.click(option);
};

// Date picker helpers (for Ant Design DatePicker)
export const selectDate = async (labelText: string | RegExp, date: Date) => {
  const user = userEvent.setup();
  
  // Find the date picker by label
  const label = screen.getByText(labelText);
  const dateInput = label.closest('.ant-form-item')?.querySelector('input');
  if (!dateInput) throw new Error('Date picker not found');
  
  // Format date as YYYY-MM-DD
  const dateString = date.toISOString().split('T')[0];
  
  // Clear and type new date
  await user.clear(dateInput);
  await user.type(dateInput, dateString);
  
  // Press Enter to confirm
  await user.keyboard('{Enter}');
};

// Modal helpers
export const waitForModal = async (title: string | RegExp) => {
  await waitFor(() => {
    const modal = screen.getByRole('dialog');
    expect(within(modal).getByText(title)).toBeInTheDocument();
  });
};

export const closeModal = async () => {
  const user = userEvent.setup();
  const closeButton = screen.getByLabelText(/close|關閉/i);
  await user.click(closeButton);
  
  await waitFor(() => {
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
};

// Message/Notification helpers
export const expectSuccessMessage = async (message: string | RegExp) => {
  await waitFor(() => {
    const successMessage = screen.getByText(message);
    expect(successMessage.closest('.ant-message-success')).toBeInTheDocument();
  });
};

export const expectErrorMessage = async (message: string | RegExp) => {
  await waitFor(() => {
    const errorMessage = screen.getByText(message);
    expect(errorMessage.closest('.ant-message-error')).toBeInTheDocument();
  });
};

// Pagination helpers
export const goToPage = async (pageNumber: number) => {
  const user = userEvent.setup();
  const pageButton = screen.getByTitle(`${pageNumber}`);
  await user.click(pageButton);
  await waitForLoadingToFinish();
};

export const changePageSize = async (size: number) => {
  const user = userEvent.setup();
  const pageSizeSelector = screen.getByTitle(/頁/);
  await user.click(pageSizeSelector);
  
  const option = screen.getByText(`${size} 條/頁`);
  await user.click(option);
  await waitForLoadingToFinish();
};

// Permission/Role helpers
export const expectElementForRole = (element: HTMLElement | null, roles: string[]) => {
  const userRole = (window as any).__TEST_USER_ROLE__ || 'office_staff';
  
  if (roles.includes(userRole)) {
    expect(element).toBeInTheDocument();
  } else {
    expect(element).not.toBeInTheDocument();
  }
};

export const expectDisabledForRole = (element: HTMLElement, roles: string[]) => {
  const userRole = (window as any).__TEST_USER_ROLE__ || 'office_staff';
  
  if (roles.includes(userRole)) {
    expect(element).toBeDisabled();
  } else {
    expect(element).not.toBeDisabled();
  }
};

// Debug helpers
export const logTestState = (label: string) => {
  if (process.env.DEBUG_TESTS) {
    // console.log(`[TEST STATE - ${label}]`);
    // console.log('Body HTML:', document.body.innerHTML);
    // console.log('---');
  }
};

export const takeScreenshot = async (name: string) => {
  if (process.env.SCREENSHOT_ON_FAILURE) {
    // This would integrate with your test runner's screenshot capability
    // For example, with Playwright:
    // await page.screenshot({ path: `screenshots/${name}.png` });
  }
};

// Async operation helpers
export const retry = async <T>(
  fn: () => Promise<T>,
  retries: number = 3,
  delay: number = 1000
): Promise<T> => {
  try {
    return await fn();
  } catch (error) {
    if (retries === 0) throw error;
    await new Promise(resolve => setTimeout(resolve, delay));
    return retry(fn, retries - 1, delay);
  }
};

// Test data helpers
export const generateTestId = (prefix: string = 'test'): string => {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

export const createFile = (name: string, content: string, type: string = 'text/plain'): File => {
  const blob = new Blob([content], { type });
  return new File([blob], name, { type });
};

// Accessibility helpers
export const expectAccessible = async (container: HTMLElement = document.body) => {
  // Check for basic accessibility
  const images = container.querySelectorAll('img');
  images.forEach(img => {
    expect(img).toHaveAttribute('alt');
  });
  
  const buttons = container.querySelectorAll('button');
  buttons.forEach(button => {
    expect(button).toHaveAccessibleName();
  });
  
  const inputs = container.querySelectorAll('input');
  inputs.forEach(input => {
    const label = container.querySelector(`label[for="${input.id}"]`);
    expect(label).toBeInTheDocument();
  });
};