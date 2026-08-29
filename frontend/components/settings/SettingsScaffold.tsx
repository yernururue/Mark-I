"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { X, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface SettingsNavItem {
  id: string;
  label: string;
  icon: LucideIcon;
}

interface SettingsScaffoldProps {
  title: ReactNode;
  items: SettingsNavItem[];
  closeHref: string;
  children: ReactNode;
}

export default function SettingsScaffold({ title, items, closeHref, children }: SettingsScaffoldProps) {
  const router = useRouter();
  
  return (
    <div 
      className="settings-scaffold-overlay" 
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          router.push(closeHref);
        }
      }}
    >
      <div className="settings-scaffold">
        <aside className="settings-local-nav">
          <nav aria-label="Settings sections">
            {items.map((item, index) => {
              const Icon = item.icon;
              return (
                <a key={item.id} href={`#${item.id}`} aria-current={index === 0 ? "location" : undefined}>
                  <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                  {item.label}
                </a>
              );
            })}
          </nav>
        </aside>

        <div className="settings-content">
          <header className="settings-content__header">
            <h1>{title}</h1>
            <Link href={closeHref} className="icon-button" aria-label="Close settings">
              <X size={20} aria-hidden="true" />
            </Link>
          </header>
          {children}
        </div>
      </div>
    </div>
  );
}
