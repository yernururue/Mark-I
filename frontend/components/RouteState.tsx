"use client";

interface RouteStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export default function RouteState({
  title = "Loading Mark-I",
  message,
  onRetry,
}: RouteStateProps) {
  return (
    <main className="route-state" aria-live="polite">
      <div className="route-state__mark" aria-hidden="true">
        M
      </div>
      <h1>{title}</h1>
      {message ? <p>{message}</p> : <div className="route-state__bar" />}
      {onRetry ? (
        <button type="button" className="button button--secondary" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </main>
  );
}
