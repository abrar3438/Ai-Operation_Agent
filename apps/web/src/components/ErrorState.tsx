import React from "react";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = "Failed to load data", message, onRetry }: ErrorStateProps) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
      <h3 className="text-sm font-semibold text-red-900">{title}</h3>
      <p className="text-xs text-red-700 mt-1">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-medium hover:bg-red-700 transition-colors"
        >
          Retry Request
        </button>
      )}
    </div>
  );
}
