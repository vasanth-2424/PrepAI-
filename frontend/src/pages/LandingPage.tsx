import { Footer } from '../components/layout/Footer';
import { Header } from '../components/layout/Header';
import { Features } from '../components/landing/Features';
import { HealthStatus } from '../components/landing/HealthStatus';
import { Hero } from '../components/landing/Hero';

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <Hero />
        <Features />
        <HealthStatus />
      </main>
      <Footer />
    </div>
  );
}
