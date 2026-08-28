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
        <h1>A mentor that pays attention to the work you actually do.</h1>
        <p>
          Mark-I watches your GitHub activity, tracks the skills you are building,
          and tells you what to work on next—without turning every commit into a notification.
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
        <span>Developer growth guidance across web and Telegram.</span>
      </footer>
    </div>
  );
}
