import GithubCallbackClient from "@/components/auth/GithubCallbackClient";

interface CallbackPageProps {
  searchParams: Promise<{ code?: string; state?: string }>;
}

export default async function GithubCallbackPage({ searchParams }: CallbackPageProps) {
  const { code, state } = await searchParams;
  return <GithubCallbackClient code={code} state={state} />;
}
