/**
 * src/components/ErrorBoundary.jsx
 * Catches render errors and shows a recovery UI.
 */
import React from 'react';
import { RefreshCw, AlertTriangle } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '60vh', gap: '16px',
          color: 'var(--text-muted)',
        }}>
          <AlertTriangle size={40} color="var(--warning)" />
          <h2 style={{ color: 'var(--text-main)', fontSize: '20px' }}>
            Something went wrong
          </h2>
          <p style={{ fontSize: '14px', maxWidth: '400px', textAlign: 'center' }}>
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <button
            className="btn btn-outline"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
          >
            <RefreshCw size={15} /> Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
