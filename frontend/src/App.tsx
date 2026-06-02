import { Dashboard } from "./components/Dashboard";
import { Footer } from "./components/Footer";

export function App() {
  return (
    <div className="flex min-h-screen flex-col bg-ink-950 scanline-grid">
      <div className="flex-1">
        <Dashboard />
      </div>
      <Footer />
    </div>
  );
}
