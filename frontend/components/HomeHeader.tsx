"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function HomeHeader() {
  const { user, loading } = useAuth();

  return (
    <header className="home-header">
      <Link href="/" className="home-brand" aria-label="Mark-I home">
        Mark-I
      </Link>
      <nav className="home-header__actions" aria-label="Account navigation">
        {!loading && user ? (
          <Link href="/dashboard" className="button button--light">
            Open dashboard
          </Link>
        ) : (
          <>
            <Link href="/login" className="home-header__login">
              Log in
            </Link>
            <Link href="/login?mode=signup" className="button button--light">
              Get started
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
