/**
 * Global error boundary — catches React rendering errors and shows
 * a user-friendly fallback UI instead of a white screen.
 */

import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary] Uncaught error:', error, info.componentStack);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-serpent-bg flex items-center justify-center p-8">
          <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-10 max-w-md text-center">
            <div className="text-[42px] mb-4 opacity-60">{'\uD83D\uDC0D'}</div>
            <h2 className="text-[18px] font-semibold font-outfit text-serpent-text-secondary mb-2">
              Something went wrong
            </h2>
            <p className="text-[12px] text-serpent-text-muted font-mono mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={this.handleReload}
              className="px-5 py-2 bg-serpent-accent text-serpent-bg text-[12px] font-mono rounded-[8px] hover:brightness-110 transition-all cursor-pointer"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
