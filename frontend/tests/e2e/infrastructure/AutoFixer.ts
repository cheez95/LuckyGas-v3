/**
 * Automatic Fix Generation and Application System
 * Generates code fixes based on error patterns and applies them iteratively
 */

import { CapturedError, ErrorCategory, ErrorSeverity } from './ErrorMonitor';
import * as fs from 'fs';
import * as path from 'path';

export interface FixSuggestion {
  errorHash: string;
  filePath: string;
  lineNumber?: number;
  originalCode?: string;
  fixedCode: string;
  description: string;
  confidence: number; // 0-1 confidence score
  applied: boolean;
  testPassed?: boolean;
}

export interface FixResult {
  success: boolean;
  fixesApplied: FixSuggestion[];
  fixesFailed: FixSuggestion[];
  message: string;
}

export class AutoFixer {
  private fixes: Map<string, FixSuggestion[]> = new Map();
  private projectRoot: string;

  constructor(projectRoot: string = process.cwd()) {
    this.projectRoot = projectRoot;
  }

  /**
   * Generate fixes for captured errors
   */
  public generateFixes(errors: CapturedError[]): FixSuggestion[] {
    const suggestions: FixSuggestion[] = [];

    errors.forEach(error => {
      if (error.autoFixable) {
        const fix = this.generateFixForError(error);
        if (fix) {
          suggestions.push(fix);
          this.addFix(error.hash, fix);
        }
      }
    });

    return suggestions;
  }

  /**
   * Generate specific fix based on error type
   */
  private generateFixForError(error: CapturedError): FixSuggestion | null {
    switch (error.category) {
      case ErrorCategory.JAVASCRIPT:
        return this.generateJavaScriptFix(error);
      case ErrorCategory.NETWORK:
        return this.generateNetworkFix(error);
      case ErrorCategory.SECURITY:
        return this.generateSecurityFix(error);
      case ErrorCategory.PERFORMANCE:
        return this.generatePerformanceFix(error);
      case ErrorCategory.WEBSOCKET:
        return this.generateWebSocketFix(error);
      case ErrorCategory.VALIDATION:
        return this.generateValidationFix(error);
      default:
        return null;
    }
  }

  /**
   * JavaScript error fixes
   */
  private generateJavaScriptFix(error: CapturedError): FixSuggestion | null {
    // Parse error message for common patterns
    const nullCheckPattern = /Cannot read prop(erty|erties) ['"]?(\w+)['"]? of (undefined|null)/i;
    const match = error.message.match(nullCheckPattern);

    if (match) {
      const propertyName = match[2];
      const filePath = this.extractFilePath(error.context.stackTrace);
      
      return {
        errorHash: error.hash,
        filePath: filePath || 'unknown',
        description: `Add null check for property '${propertyName}'`,
        fixedCode: this.generateNullCheckCode(propertyName),
        confidence: 0.8,
        applied: false,
      };
    }

    // Type error fixes
    if (error.message.includes('TypeError')) {
      return {
        errorHash: error.hash,
        filePath: this.extractFilePath(error.context.stackTrace) || 'unknown',
        description: 'Add type validation and default values',
        fixedCode: this.generateTypeValidationCode(),
        confidence: 0.7,
        applied: false,
      };
    }

    return null;
  }

  /**
   * Network error fixes
   */
  private generateNetworkFix(error: CapturedError): FixSuggestion | null {
    if (error.message.includes('Failed to fetch')) {
      return {
        errorHash: error.hash,
        filePath: 'src/services/api.ts',
        description: 'Add retry logic with exponential backoff',
        fixedCode: `
// Retry logic with exponential backoff
async function fetchWithRetry(url: string, options: RequestInit = {}, maxRetries = 3): Promise<Response> {
  let lastError: Error | null = null;
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, {
        ...options,
        signal: AbortSignal.timeout(10000), // 10 second timeout
      });
      
      if (!response.ok && response.status >= 500) {
        throw new Error(\`Server error: \${response.status}\`);
      }
      
      return response;
    } catch (error) {
      lastError = error as Error;
      
      // Don't retry on client errors
      if (error instanceof Error && error.message.includes('4')) {
        throw error;
      }
      
      // Exponential backoff
      if (i < maxRetries - 1) {
        const delay = Math.min(1000 * Math.pow(2, i), 10000);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError || new Error('Max retries exceeded');
}`,
        confidence: 0.9,
        applied: false,
      };
    }

    return null;
  }

  /**
   * Security error fixes
   */
  private generateSecurityFix(error: CapturedError): FixSuggestion | null {
    if (error.message.includes('Mixed Content')) {
      return {
        errorHash: error.hash,
        filePath: 'src/services/api.ts',
        description: 'Force HTTPS for all API calls',
        fixedCode: `
// Force HTTPS for security
function enforceHTTPS(url: string): string {
  if (url.startsWith('http://') && !url.includes('localhost')) {
    console.warn('Converting HTTP to HTTPS for security:', url);
    return url.replace('http://', 'https://');
  }
  return url;
}

// Apply to all API calls
const secureUrl = enforceHTTPS(apiUrl);`,
        confidence: 0.95,
        applied: false,
      };
    }

    if (error.message.includes('CORS')) {
      return {
        errorHash: error.hash,
        filePath: 'backend/app/main.py',
        description: 'Update CORS configuration',
        fixedCode: `
# Update CORS configuration
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vast-tributary-466619-m8.web.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)`,
        confidence: 0.85,
        applied: false,
      };
    }

    return null;
  }

  /**
   * Performance error fixes
   */
  private generatePerformanceFix(error: CapturedError): FixSuggestion | null {
    if (error.message.includes('memory leak')) {
      return {
        errorHash: error.hash,
        filePath: 'src/components/',
        description: 'Add proper cleanup in useEffect',
        fixedCode: `
// Proper cleanup to prevent memory leaks
useEffect(() => {
  const controller = new AbortController();
  let mounted = true;
  
  const fetchData = async () => {
    try {
      const response = await fetch(url, { signal: controller.signal });
      const data = await response.json();
      
      if (mounted) {
        setData(data);
      }
    } catch (error) {
      if (mounted && error.name !== 'AbortError') {
        setError(error);
      }
    }
  };
  
  fetchData();
  
  return () => {
    mounted = false;
    controller.abort();
  };
}, [url]);`,
        confidence: 0.8,
        applied: false,
      };
    }

    if (error.message.includes('Long task')) {
      return {
        errorHash: error.hash,
        filePath: 'src/utils/',
        description: 'Move heavy computation to Web Worker',
        fixedCode: `
// Web Worker for heavy computations
const worker = new Worker(new URL('./heavy-computation.worker.ts', import.meta.url));

worker.postMessage({ command: 'process', data: largeDataSet });

worker.onmessage = (event) => {
  const { result } = event.data;
  // Handle result
};

// heavy-computation.worker.ts
self.onmessage = (event) => {
  const { command, data } = event.data;
  
  if (command === 'process') {
    // Heavy computation here
    const result = processData(data);
    self.postMessage({ result });
  }
};`,
        confidence: 0.75,
        applied: false,
      };
    }

    return null;
  }

  /**
   * WebSocket error fixes
   */
  private generateWebSocketFix(error: CapturedError): FixSuggestion | null {
    if (error.message.includes('WebSocket') || error.message.includes('connection closed')) {
      return {
        errorHash: error.hash,
        filePath: 'src/services/websocket.service.ts',
        description: 'Add WebSocket reconnection logic',
        fixedCode: `
// WebSocket with automatic reconnection
class ReconnectingWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;
  
  constructor(url: string) {
    this.url = url;
    this.connect();
  }
  
  private connect(): void {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.reconnectInterval = 1000;
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.attemptReconnect();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.ws?.close();
      };
      
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.attemptReconnect();
    }
  }
  
  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(\`Reconnecting... Attempt \${this.reconnectAttempts}\`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectInterval);
      
      // Exponential backoff
      this.reconnectInterval = Math.min(this.reconnectInterval * 2, 30000);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }
  
  public send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, queuing message');
      // Implement message queue if needed
    }
  }
  
  public close(): void {
    this.maxReconnectAttempts = 0; // Prevent reconnection
    this.ws?.close();
  }
}`,
        confidence: 0.85,
        applied: false,
      };
    }

    return null;
  }

  /**
   * Validation error fixes
   */
  private generateValidationFix(error: CapturedError): FixSuggestion | null {
    if (error.message.includes('validation') || error.message.includes('required field')) {
      return {
        errorHash: error.hash,
        filePath: 'src/utils/validators.ts',
        description: 'Add comprehensive form validation',
        fixedCode: `
// Form validation utilities
export const validators = {
  required: (value: any) => {
    if (value === null || value === undefined || value === '') {
      return 'This field is required';
    }
    return null;
  },
  
  email: (value: string) => {
    const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    if (!emailRegex.test(value)) {
      return 'Please enter a valid email address';
    }
    return null;
  },
  
  phone: (value: string) => {
    // Taiwan phone number format
    const phoneRegex = /^09\\d{2}-?\\d{3}-?\\d{3}$|^0[2-8]-?\\d{7,8}$/;
    if (!phoneRegex.test(value)) {
      return 'Please enter a valid Taiwan phone number';
    }
    return null;
  },
  
  minLength: (min: number) => (value: string) => {
    if (value.length < min) {
      return \`Minimum length is \${min} characters\`;
    }
    return null;
  },
  
  maxLength: (max: number) => (value: string) => {
    if (value.length > max) {
      return \`Maximum length is \${max} characters\`;
    }
    return null;
  },
};

// Validate form data
export function validateForm(data: any, rules: any): Record<string, string> {
  const errors: Record<string, string> = {};
  
  Object.keys(rules).forEach(field => {
    const fieldRules = rules[field];
    const value = data[field];
    
    for (const rule of fieldRules) {
      const error = rule(value);
      if (error) {
        errors[field] = error;
        break;
      }
    }
  });
  
  return errors;
}`,
        confidence: 0.8,
        applied: false,
      };
    }

    return null;
  }

  /**
   * Helper methods
   */
  private generateNullCheckCode(propertyName: string): string {
    return `
// Null check for ${propertyName}
if (object && object.${propertyName}) {
  // Safe to use object.${propertyName}
  const value = object.${propertyName};
} else {
  // Handle null/undefined case
  console.warn('${propertyName} is null or undefined');
  const value = defaultValue; // Provide appropriate default
}

// Or using optional chaining
const value = object?.${propertyName} ?? defaultValue;`;
  }

  private generateTypeValidationCode(): string {
    return `
// Type validation utility
function validateType(value: any, expectedType: string): boolean {
  if (expectedType === 'array') {
    return Array.isArray(value);
  }
  return typeof value === expectedType;
}

// Safe type conversion
function safeConvert<T>(value: any, defaultValue: T): T {
  try {
    if (value === null || value === undefined) {
      return defaultValue;
    }
    return value as T;
  } catch {
    return defaultValue;
  }
}`;
  }

  private extractFilePath(stackTrace?: string): string | null {
    if (!stackTrace) return null;
    
    // Extract file path from stack trace
    const match = stackTrace.match(/([^:]+\.(ts|tsx|js|jsx)):\d+:\d+/);
    if (match) {
      return match[1];
    }
    
    return null;
  }

  private addFix(errorHash: string, fix: FixSuggestion): void {
    const fixes = this.fixes.get(errorHash) || [];
    fixes.push(fix);
    this.fixes.set(errorHash, fixes);
  }

  /**
   * Apply fixes to files (simulation - in real scenario, use file system operations)
   */
  public async applyFixes(fixes: FixSuggestion[]): Promise<FixResult> {
    const result: FixResult = {
      success: true,
      fixesApplied: [],
      fixesFailed: [],
      message: '',
    };

    for (const fix of fixes) {
      if (fix.confidence < 0.7) {
        console.log(`Skipping fix with low confidence (${fix.confidence}): ${fix.description}`);
        continue;
      }

      try {
        // In a real implementation, this would modify actual files
        console.log(`Applying fix: ${fix.description}`);
        console.log(`File: ${fix.filePath}`);
        console.log(`Code:\n${fix.fixedCode}`);
        
        fix.applied = true;
        result.fixesApplied.push(fix);
      } catch (error) {
        console.error(`Failed to apply fix: ${fix.description}`, error);
        result.fixesFailed.push(fix);
        result.success = false;
      }
    }

    result.message = `Applied ${result.fixesApplied.length} fixes, ${result.fixesFailed.length} failed`;
    return result;
  }

  /**
   * Generate fix report
   */
  public generateFixReport(fixes: FixSuggestion[]): string {
    const applied = fixes.filter(f => f.applied);
    const pending = fixes.filter(f => !f.applied);
    
    return `
# Auto-Fix Report

## Summary
- Total fixes suggested: ${fixes.length}
- Applied: ${applied.length}
- Pending: ${pending.length}

## Applied Fixes
${applied.map(fix => `
### ${fix.description}
- File: ${fix.filePath}
- Confidence: ${(fix.confidence * 100).toFixed(0)}%
- Test Result: ${fix.testPassed ? 'PASSED' : 'PENDING'}
`).join('\n')}

## Pending Fixes
${pending.map(fix => `
### ${fix.description}
- File: ${fix.filePath}
- Confidence: ${(fix.confidence * 100).toFixed(0)}%
- Reason: ${fix.confidence < 0.7 ? 'Low confidence' : 'Manual review required'}
`).join('\n')}

## Fix Code Snippets
${fixes.map(fix => `
### ${fix.description}
\`\`\`typescript
${fix.fixedCode}
\`\`\`
`).join('\n')}
`;
  }

  public reset(): void {
    this.fixes.clear();
  }
}