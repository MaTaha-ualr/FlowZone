import { Link } from "react-router-dom";
import { Compass, Home } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function NotFound() {
  const { isAuthenticated } = useAuth();
  const homeTo = isAuthenticated ? "/dashboard" : "/";

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brandGold/10">
        <Compass className="h-8 w-8 text-brandGold" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <p className="font-display text-6xl tracking-widest text-brandGold text-glow-gold">404</p>
        <h1 className="font-display text-2xl tracking-wide text-textPrimary">Page not found</h1>
        <p className="max-w-sm text-sm text-textSecondary">
          This page doesn&apos;t exist or may have moved. Let&apos;s get you back somewhere useful.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          to={homeTo}
          className="inline-flex items-center gap-2 rounded-fz-md bg-brandGold px-4 py-2 text-sm font-medium text-textInverse transition-colors hover:bg-brandGoldBright"
        >
          <Home size={16} aria-hidden="true" />
          {isAuthenticated ? "Back to dashboard" : "Back home"}
        </Link>
      </div>
    </div>
  );
}
