import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback. Receives the error and a reset callback. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** Short label used in the default fallback copy, e.g. "FlowQuest". */
  label?: string;
  /** Notified when an error is caught. Wire to a monitoring service later. */
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render/runtime errors in its subtree so a single broken component
 * cannot blank the whole app. Use one at the app root and around high-risk
 * flows (FlowQuest, Voice) so a failure there degrades locally.
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface in dev; a real monitoring hook can be attached via onError.
    if (import.meta.env.DEV) {
      console.error("ErrorBoundary caught an error:", error, info);
    }
    this.props.onError?.(error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) return this.props.fallback(error, this.reset);

    const label = this.props.label ?? "this area";
    return (
      <div
        role="alert"
        className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-6 text-center"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-safeRed/10">
          <AlertTriangle className="h-7 w-7 text-safeRed" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <h2 className="font-display text-2xl tracking-wide text-textPrimary">
            Something went wrong
          </h2>
          <p className="max-w-sm text-sm text-textSecondary">
            We hit an unexpected problem loading {label}. Your data is safe. You can try again, and
            if it keeps happening, reach out for support.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={this.reset}
            className="inline-flex items-center gap-2 rounded-fz-md bg-brandGold px-4 py-2 text-sm font-medium text-textInverse transition-colors hover:bg-brandGoldBright"
          >
            <RefreshCw size={16} aria-hidden="true" />
            Try again
          </button>
          <a
            href="#/dashboard"
            className="inline-flex items-center gap-2 rounded-fz-md border border-borderSubtle px-4 py-2 text-sm font-medium text-textSecondary transition-colors hover:text-textPrimary"
          >
            Back to dashboard
          </a>
        </div>
      </div>
    );
  }
}
