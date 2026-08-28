import GithubCallbackClient from "@/components/auth/GithubCallbackClient";

interface CallbackPageProps {
  searchParams: Promise<{ code?: string }>;
}

export default async function GithubCallbackPage({ searchParams }: CallbackPageProps) {
  const { code } = await searchParams;
  return <GithubCallbackClient code={code} />;
}
