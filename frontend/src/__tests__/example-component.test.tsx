import React from 'react';
import { render, screen, fireEvent, waitFor } from './test-utils';
import { useAuth } from '../contexts/AuthContext';
import { useWebSocketContext } from '../contexts/WebSocketContext';
import { useTranslation } from 'react-i18next';

// Example component using hooks and context
const ExampleComponent: React.FC = () => {
  const { user } = useAuth();
  const { isConnected } = useWebSocketContext();
  const { t } = useTranslation();
  const [count, setCount] = React.useState(0);

  const handleClick = () => {
    setCount(prev => prev + 1);
  };

  return (
    <div>
      <h1>{t('welcome')}</h1>
      <p>User: {user?.username || 'Guest'}</p>
      <p>WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</p>
      <button onClick={handleClick}>Count: {count}</button>
    </div>
  );
};

describe('ExampleComponent', () => {
  it('should render with mocked contexts', () => {
    render(<ExampleComponent />);
    
    // Check that component renders
    expect(screen.getByText('welcome')).toBeInTheDocument();
    expect(screen.getByText('User: testuser')).toBeInTheDocument();
    expect(screen.getByText('WebSocket: Connected')).toBeInTheDocument();
  });

  it('should handle state updates', async () => {
    render(<ExampleComponent />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Count: 0');
    
    // Click the button
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(button).toHaveTextContent('Count: 1');
    });
  });

  it('should use mocked translation', () => {
    render(<ExampleComponent />);
    
    // The translation mock returns the key, so we should see 'welcome'
    expect(screen.getByText('welcome')).toBeInTheDocument();
  });

  it('should access mocked auth context', () => {
    render(<ExampleComponent />);
    
    // The auth mock provides a testuser
    expect(screen.getByText(/User: testuser/)).toBeInTheDocument();
  });

  it('should access mocked WebSocket context', () => {
    render(<ExampleComponent />);
    
    // The WebSocket mock shows as connected
    expect(screen.getByText(/WebSocket: Connected/)).toBeInTheDocument();
  });
});