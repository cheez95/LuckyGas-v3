import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Login from '../../../components/Login';
import { AuthProvider } from '../../../contexts/AuthContext';
import * as authService from '../../../services/auth.service';

// Mock auth service
jest.mock('../../../services/auth.service');

// Mock navigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock antd message
jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  message: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const renderLogin = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('Login Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders login form with all elements', () => {
    renderLogin();
    
    expect(screen.getByText('auth.login')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('auth.usernamePlaceholder')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('auth.passwordPlaceholder')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'auth.loginButton' })).toBeInTheDocument();
  });

  it('displays validation errors for empty fields', async () => {
    renderLogin();
    
    const loginButton = screen.getByRole('button', { name: 'auth.loginButton' });
    
    await userEvent.click(loginButton);
    
    await waitFor(() => {
      expect(screen.getByText('auth.usernameRequired')).toBeInTheDocument();
      expect(screen.getByText('auth.passwordRequired')).toBeInTheDocument();
    });
  });

  it('handles successful login', async () => {
    const mockUser = {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      role: 'admin',
      permissions: ['manage_users'],
    };
    
    const mockLoginResponse = {
      access_token: 'mock-token',
      token_type: 'bearer',
      user: mockUser,
    };
    
    (authService.login as jest.Mock).mockResolvedValue(mockLoginResponse);
    
    renderLogin();
    
    const usernameInput = screen.getByPlaceholderText('auth.usernamePlaceholder');
    const passwordInput = screen.getByPlaceholderText('auth.passwordPlaceholder');
    const loginButton = screen.getByRole('button', { name: 'auth.loginButton' });
    
    await userEvent.type(usernameInput, 'testuser');
    await userEvent.type(passwordInput, 'password123');
    await userEvent.click(loginButton);
    
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('testuser', 'password123');
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('handles login failure', async () => {
    const mockError = new Error('Invalid credentials');
    (authService.login as jest.Mock).mockRejectedValue(mockError);
    
    renderLogin();
    
    const usernameInput = screen.getByPlaceholderText('auth.usernamePlaceholder');
    const passwordInput = screen.getByPlaceholderText('auth.passwordPlaceholder');
    const loginButton = screen.getByRole('button', { name: 'auth.loginButton' });
    
    await userEvent.type(usernameInput, 'testuser');
    await userEvent.type(passwordInput, 'wrongpassword');
    await userEvent.click(loginButton);
    
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('testuser', 'wrongpassword');
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('disables submit button while loading', async () => {
    (authService.login as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    );
    
    renderLogin();
    
    const usernameInput = screen.getByPlaceholderText('auth.usernamePlaceholder');
    const passwordInput = screen.getByPlaceholderText('auth.passwordPlaceholder');
    const loginButton = screen.getByRole('button', { name: 'auth.loginButton' });
    
    await userEvent.type(usernameInput, 'testuser');
    await userEvent.type(passwordInput, 'password123');
    
    expect(loginButton).not.toBeDisabled();
    
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      expect(loginButton).toBeDisabled();
    });
  });

  it('supports keyboard navigation', async () => {
    renderLogin();
    
    const usernameInput = screen.getByPlaceholderText('auth.usernamePlaceholder');
    const passwordInput = screen.getByPlaceholderText('auth.passwordPlaceholder');
    
    // Focus should move between inputs with Tab
    usernameInput.focus();
    expect(document.activeElement).toBe(usernameInput);
    
    await userEvent.tab();
    expect(document.activeElement).toBe(passwordInput);
  });

  it('handles Enter key submission', async () => {
    (authService.login as jest.Mock).mockResolvedValue({
      access_token: 'mock-token',
      token_type: 'bearer',
      user: { id: 1, username: 'testuser' },
    });
    
    renderLogin();
    
    const usernameInput = screen.getByPlaceholderText('auth.usernamePlaceholder');
    const passwordInput = screen.getByPlaceholderText('auth.passwordPlaceholder');
    
    await userEvent.type(usernameInput, 'testuser');
    await userEvent.type(passwordInput, 'password123');
    
    // Press Enter in password field
    await userEvent.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('testuser', 'password123');
    });
  });
});