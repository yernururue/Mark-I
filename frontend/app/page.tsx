import Image from "next/image";
import Link from "next/link";
import HomeHeader from "@/components/HomeHeader";

export default function Home() {
  return (
    <div className="home-page">
      <HomeHeader />
      <Image
        src="/background/city.png"
        alt="A night city skyline viewed across the water"
        fill
        priority
        sizes="100vw"
        className="home-page__image"
      />
      <div className="home-page__shade" aria-hidden="true" />
      <div className="home-page__grain" aria-hidden="true" />

      <main className="home-hero">
        <h1>Build a team of agents that works your way.</h1>
        <p>
          Create specialized agents, control what each one can access, and run work in parallel
          with clear ownership, outputs, and handoffs.
        </p>
        <div className="home-hero__actions">
          <Link href="/login?mode=signup" className="button button--light">
            Set up Mark-I
          </Link>
          <Link href="/login" className="button button--dark">
            Continue to your account
          </Link>
        </div>
      </main>

      <footer className="home-footer">
        <span>Configurable agents across web, GitHub, and Telegram.</span>
      </footer>
    </div>
  );
}
