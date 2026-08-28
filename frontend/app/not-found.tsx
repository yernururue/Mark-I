import Link from "next/link";

export default function NotFound() {
  return (
    <main className="not-found">
      <span className="not-found__code">404</span>
      <h1>This page does not exist</h1>
      <p>The link may be outdated, or the page may have moved.</p>
      <Link href="/dashboard" className="button button--primary">
        Return to dashboard
      </Link>
    </main>
  );
}
