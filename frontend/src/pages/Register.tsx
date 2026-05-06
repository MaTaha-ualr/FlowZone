import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Eye, EyeOff, AlertTriangle, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface RegisterForm {
  name: string;
  username: string;
  password: string;
  confirmPassword: string;
  email: string;
  phone: string;
  age: number;
  role: "youth" | "mentor";
  school_name: string;
  city: string;
  state: string;
  user_type: "at_risk" | "juvenile_justice";
  has_probation: boolean;
  has_case_worker: boolean;
}

export default function Register() {
  const { register, isLoading } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<RegisterForm>({
    name: "",
    username: "",
    password: "",
    confirmPassword: "",
    email: "",
    phone: "",
    age: 15,
    role: "youth",
    school_name: "",
    city: "",
    state: "",
    user_type: "at_risk",
    has_probation: false,
    has_case_worker: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  function update<K extends keyof RegisterForm>(k: K, v: RegisterForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  const strength =
    form.password.length === 0 ? 0 : form.password.length < 6 ? 1 : form.password.length < 10 ? 2 : 3;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    try {
      const { confirmPassword: _drop, ...payload } = form;
      void _drop;
      await register(payload);
      navigate(form.role === "mentor" ? "/mentor/dashboard" : "/vibe-check");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="min-h-screen bg-fz-base py-12 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-lg mx-auto"
      >
        <div className="text-center mb-8">
          <h1 className="font-display text-5xl text-fz-gold tracking-wider text-glow-gold">GET IN</h1>
          <p className="text-text-secondary mt-2">Create your FlowZone account.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            placeholder="Full Name"
            className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
            required
          />
          <input
            value={form.username}
            onChange={(e) => update("username", e.target.value)}
            placeholder="Username"
            autoComplete="username"
            className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
            required
          />

          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              placeholder="Password"
              autoComplete="new-password"
              className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none pr-12 transition-colors"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>

          {form.password && (
            <div className="flex gap-1">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className={`h-1.5 flex-1 rounded-full transition-colors ${
                    i <= strength
                      ? strength === 1
                        ? "bg-safe-red"
                        : strength === 2
                        ? "bg-safe-yellow"
                        : "bg-tier-flex"
                      : "bg-fz-border"
                  }`}
                />
              ))}
            </div>
          )}

          <input
            type="password"
            value={form.confirmPassword}
            onChange={(e) => update("confirmPassword", e.target.value)}
            placeholder="Confirm Password"
            autoComplete="new-password"
            className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              value={form.age}
              onChange={(e) => update("age", parseInt(e.target.value) || 0)}
              placeholder="Age"
              className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
              min={12}
              max={25}
            />
            <select
              value={form.role}
              onChange={(e) => update("role", e.target.value as "youth" | "mentor")}
              className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
            >
              <option value="youth">Youth</option>
              <option value="mentor">Mentor</option>
            </select>
          </div>

          <AnimatePresence initial={false}>
            {form.role === "youth" && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="space-y-4 overflow-hidden"
              >
                <select
                  value={form.user_type}
                  onChange={(e) =>
                    update("user_type", e.target.value as "at_risk" | "juvenile_justice")
                  }
                  className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
                >
                  <option value="at_risk">At-Risk</option>
                  <option value="juvenile_justice">Juvenile Justice</option>
                </select>

                <div className="grid grid-cols-2 gap-3">
                  <input
                    value={form.school_name}
                    onChange={(e) => update("school_name", e.target.value)}
                    placeholder="School (optional)"
                    className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
                  />
                  <input
                    value={form.city}
                    onChange={(e) => update("city", e.target.value)}
                    placeholder="City (optional)"
                    className="w-full px-4 py-3 bg-fz-overlay border border-fz-border rounded-lg text-text-primary focus:border-fz-gold focus:outline-none transition-colors"
                  />
                </div>

                <div className="flex flex-wrap gap-4 text-sm text-text-secondary">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.has_probation}
                      onChange={(e) => update("has_probation", e.target.checked)}
                      className="rounded border-fz-border bg-fz-overlay accent-fz-gold"
                    />
                    On Probation
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.has_case_worker}
                      onChange={(e) => update("has_case_worker", e.target.checked)}
                      className="rounded border-fz-border bg-fz-overlay accent-fz-gold"
                    />
                    Has Case Worker
                  </label>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {error && (
            <div className="flex items-center gap-2 px-4 py-3 bg-safe-red/10 border border-safe-red/30 rounded-lg text-sm text-safe-red">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-3.5 bg-fz-gold text-text-inverse font-semibold rounded-lg hover:bg-fz-gold-bright transition-colors disabled:opacity-50"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-text-inverse border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Zap className="w-5 h-5" /> CREATE ACCOUNT
              </>
            )}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-text-muted">
          Already have an account?{" "}
          <Link to="/login" className="text-fz-gold hover:text-fz-gold-bright">
            Sign In
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
