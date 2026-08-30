import Link from "next/link";
import AuthForm from "@/components/auth/AuthForm";

interface LoginPageProps {
  searchParams: Promise<{ mode?: string; next?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;

  return (
    <main className="auth-page">
      <Link href="/" className="auth-page__brand" aria-label="Back to Mark-I home">
        Mark-I
      </Link>
      <AuthForm
        initialMode={params.mode === "signup" ? "signup" : "login"}
        nextPath={params.next}
      />
      <p className="auth-page__footnote">
        Your account controls access. GitHub and Telegram connections are managed separately in Settings.
      </p>
    </main>
  );
}
