import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Simple component to test React 19 compatibility
const TestComponent: React.FC<{ message: string }> = ({ message }) => {
  return (
    <div>
      <h1>Test Component</h1>
      <p>{message}</p>
    </div>
  );
};

describe('Test Infrastructure', () => {
  it('should render a simple component with React 19', () => {
    render(<TestComponent message="Hello from React 19!" />);
    
    expect(screen.getByText('Test Component')).toBeInTheDocument();
    expect(screen.getByText('Hello from React 19!')).toBeInTheDocument();
  });

  it('should handle TypeScript types correctly', () => {
    const props = { message: 'TypeScript works!' };
    const { container } = render(<TestComponent {...props} />);
    
    expect(container).toBeTruthy();
  });

  it('should mock import.meta.env correctly', () => {
    // Access through global mock instead of direct import.meta
    expect((global as any).import.meta.env.VITE_API_URL).toBe('http://localhost:8000');
    expect((global as any).import.meta.env.VITE_WS_URL).toBe('ws://localhost:8000');
    expect((global as any).import.meta.env.VITE_ENV).toBe('test');
  });

  it('should have WebSocket mock available', () => {
    const ws = new WebSocket('ws://localhost:8000');
    expect(ws).toBeDefined();
    expect(ws.readyState).toBe(1); // OPEN state
  });

  it('should have matchMedia mock available', () => {
    const mediaQuery = window.matchMedia('(min-width: 768px)');
    expect(mediaQuery).toBeDefined();
    expect(mediaQuery.matches).toBe(false);
  });
});