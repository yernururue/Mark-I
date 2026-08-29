"use client";

import { useState } from "react";
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
  variant?: "page" | "modal";
}

export default function SettingsScaffold({ title, items, closeHref, children, variant = "page" }: SettingsScaffoldProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState(items[0]?.id);
  
  const isModal = variant === "modal";

  const scaffold = (
    <div className="settings-scaffold" data-variant={variant}>
      <aside className="settings-local-nav">
        <nav aria-label="Settings sections">
          {items.map((item, index) => {
            const Icon = item.icon;
            if (isModal) {
              return (
                <button 
                  key={item.id} 
                  type="button"
                  className="settings-nav-button"
                  aria-current={activeTab === item.id ? "page" : undefined}
                  onClick={() => setActiveTab(item.id)}
                >
                  <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                  {item.label}
                </button>
              );
            }
            return (
              <a key={item.id} href={`#${item.id}`} aria-current={index === 0 ? "location" : undefined} className="settings-nav-button">
                <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                {item.label}
              </a>
            );
          })}
        </nav>
      </aside>

      <div className="settings-content" data-active-tab={isModal ? activeTab : undefined}>
        <header className="settings-content__header">
          <h1>{title}</h1>
          <Link href={closeHref} className="icon-button" aria-label="Close settings">
            <X size={20} aria-hidden="true" />
          </Link>
        </header>
        {children}
      </div>
    </div>
  );

  if (isModal) {
    return (
      <div 
        className="settings-scaffold-overlay" 
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            router.push(closeHref);
          }
        }}
      >
        {scaffold}
      </div>
    );
  }

  return scaffold;
}
