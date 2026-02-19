import React, { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
      
      const isConfigError = !supabaseUrl || !supabaseKey;
      
      return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center px-4">
          <div className="max-w-md w-full bg-gray-800 rounded-xl shadow-2xl border border-red-700 p-8">
            <div className="text-center">
              <div className="text-6xl mb-4">⚠️</div>
              <h1 className="text-2xl font-bold text-red-400 mb-4">Configuration Error</h1>
              
              {isConfigError ? (
                <>
                  <p className="text-gray-300 mb-6">
                    Missing Supabase configuration. Please set up your environment variables.
                  </p>
                  <div className="bg-gray-900 rounded-lg p-4 mb-6 text-left">
                    <p className="text-sm text-gray-400 mb-2">Create a <code className="bg-gray-800 px-2 py-1 rounded">.env</code> file in the frontend directory:</p>
                    <pre className="text-xs text-green-400 overflow-x-auto">
{`VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:5000`}
                    </pre>
                  </div>
                  <p className="text-sm text-gray-400">
                    Then restart the dev server: <code className="bg-gray-900 px-2 py-1 rounded">npm run dev</code>
                  </p>
                </>
              ) : (
                <>
                  <p className="text-gray-300 mb-4">
                    An error occurred: {this.state.error?.message}
                  </p>
                  <button
                    onClick={() => window.location.reload()}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
                  >
                    Reload Page
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
