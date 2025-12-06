import React from 'react';

class JobBuilderErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('CompleteJobBuilder Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-50 border border-red-200 rounded p-6 m-4">
          <h3 className="text-red-800 font-bold text-lg mb-2">⚠️ Component Error</h3>
          <p className="text-red-600 mb-4">Something went wrong loading the Job Builder.</p>
          <details className="text-sm text-gray-600">
            <summary className="cursor-pointer font-medium mb-2">Error Details</summary>
            <pre className="bg-red-100 p-2 rounded text-xs overflow-auto">
              {this.state.error?.toString()}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default JobBuilderErrorBoundary;
