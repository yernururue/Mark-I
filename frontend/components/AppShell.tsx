"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, LogOut, MessageSquare, Settings } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import type { ReactNode } from "react";

const NAVIGATION = [
  { href: "/dashboard", label: "Dashboard", icon: Activity },
  { href: "/chat", label: "Mentor chat", icon: MessageSquare },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();

  const handleSignOut = async () => {
    await signOut();
    router.replace("/");
  };

  const accountName = user?.displayName || user?.email || "Mark-I account";

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>

      <aside className="app-sidebar">
        <Link href="/dashboard" className="app-brand" aria-label="Mark-I dashboard">
          Mark-I
        </Link>

        <nav className="app-nav" aria-label="Main navigation">
          {NAVIGATION.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="app-nav__link"
                aria-current={active ? "page" : undefined}
              >
                <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="app-account">
          <span className="app-account__avatar" aria-hidden="true">
            {accountName.charAt(0).toUpperCase()}
          </span>
          <span className="app-account__name" title={accountName}>
            {accountName}
          </span>
          <button
            type="button"
            className="icon-button"
            onClick={handleSignOut}
            aria-label="Sign out"
          >
            <LogOut size={17} aria-hidden="true" />
          </button>
        </div>
      </aside>

      <main id="main-content" className="app-main">
        {children}
      </main>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        {NAVIGATION.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="mobile-nav__link"
              aria-current={active ? "page" : undefined}
            >
              <Icon size={19} aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
