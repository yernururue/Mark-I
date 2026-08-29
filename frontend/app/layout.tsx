import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Mark-I — Multi-agent workspace",
    template: "%s · Mark-I",
  },
  description: "Create configurable AI agents, run work in parallel, and keep every action, output, and handoff attributable.",
  applicationName: "Mark-I",
  openGraph: {
    title: "Mark-I — Multi-agent workspace",
    description: "A configurable workspace for specialized AI agents.",
    type: "website",
  },
};

import { AuthProvider } from "@/contexts/AuthContext";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
