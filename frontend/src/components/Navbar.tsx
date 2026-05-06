import { Link, useLocation } from "react-router-dom";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Menu,
  X,
  LogOut,
  Shield,
  Zap,
  BarChart3,
  Star,
  Heart,
  MessageSquare,
  Mic,
  FileText,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const youthLinks = [
  { to: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { to: "/flowquest", label: "FlowQuest", icon: MessageSquare },
  { to: "/vibe-check", label: "Vibe Check", icon: Heart },
  { to: "/trust", label: "Trust", icon: Shield },
  { to: "/rewards", label: "Rewards", icon: Star },
  { to: "/voice", label: "Voice", icon: Mic },
  { to: "/documents", label: "Documents", icon: FileText },
];

const mentorLinks = [
  { to: "/mentor/dashboard", label: "Dashboard", icon: BarChart3 },
];

export default function Navbar() {
  const { user, isAuthenticated, logout, role } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = role === "mentor" ? mentorLinks : youthLinks;

  return (
    <nav className="sticky top-0 z-50 bg-bgElevated/90 backdrop-blur-md border-b border-borderSubtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-2">
            <span className="font-display text-2xl tracking-widest text-brandGold text-glow-gold">
              FLOWZONE
            </span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-1">
            {isAuthenticated &&
              links.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-fz-md text-sm font-medium transition-colors ${
                    location.pathname === l.to || location.pathname.startsWith(l.to + "/")
                      ? "text-brandGold bg-brandGold/10"
                      : "text-textSecondary hover:text-textPrimary hover:bg-bgHover"
                  }`}
                >
                  <l.icon size={16} />
                  {l.label}
                </Link>
              ))}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {isAuthenticated && user && (
              <>
                <div className="hidden sm:flex items-center gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor:
                        user.safe_harbor_floor === "green"
                          ? "#10B981"
                          : user.safe_harbor_floor === "yellow"
                          ? "#F59E0B"
                          : "#DC2626",
                    }}
                  />
                  <span className="text-sm font-medium text-brandGold">
                    {user.display_score}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="hidden md:flex items-center gap-1.5 text-textMuted hover:text-safeRed transition-colors text-sm"
                >
                  <LogOut size={16} />
                  Exit
                </button>
              </>
            )}

            {!isAuthenticated && (
              <Link
                to="/login"
                className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-fz-md bg-brandGold text-textInverse text-sm font-medium hover:bg-brandGoldBright transition-colors"
              >
                <Zap size={14} />
                Get In
              </Link>
            )}

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 text-textPrimary"
            >
              {mobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden overflow-hidden border-t border-borderSubtle bg-bgElevated"
          >
            <div className="px-4 py-3 space-y-1">
              {isAuthenticated ? (
                <>
                  {links.map((l) => (
                    <Link
                      key={l.to}
                      to={l.to}
                      onClick={() => setMobileOpen(false)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-fz-md text-sm ${
                        location.pathname === l.to
                          ? "text-brandGold bg-brandGold/10"
                          : "text-textSecondary"
                      }`}
                    >
                      <l.icon size={16} />
                      {l.label}
                    </Link>
                  ))}
                  <button
                    onClick={() => {
                      setMobileOpen(false);
                      logout();
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-safeRed"
                  >
                    <LogOut size={16} />
                    Exit
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-brandGold"
                >
                  <Zap size={16} />
                  Get In
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
