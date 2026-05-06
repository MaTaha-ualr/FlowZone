import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Flame, Zap, Shield, Target, TrendingUp, Users, ChevronDown } from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.1, duration: 0.6 } }),
};

export default function Home() {
  return (
    <div className="min-h-screen bg-fz-base text-text-primary overflow-x-hidden -mx-4 md:-mx-8 -mt-8">
      {/* HERO */}
      <section className="relative min-h-[88vh] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(212,175,55,0.10),transparent_55%),radial-gradient(circle_at_75%_70%,rgba(0,168,232,0.10),transparent_55%)]" />
        <div className="absolute inset-0 bg-noise opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-b from-fz-base/60 via-fz-base/80 to-fz-base" />

        <div className="relative z-10 text-center px-4 max-w-4xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-fz-elevated border border-fz-border mb-8">
              <span className="w-2 h-2 rounded-full bg-safe-green animate-pulse" />
              <span className="text-xs text-text-secondary tracking-wide">TRUST ENGINE v0.2.1</span>
            </div>
            <h1 className="font-display text-5xl md:text-7xl lg:text-8xl text-fz-gold tracking-wider leading-none mb-6 text-glow-gold">
              THEY WATCH.
              <br />
              <span className="text-text-primary">YOU FLEX.</span>
              <br />
              <span className="text-fz-gold-bright">YOU GET VETTED.</span>
            </h1>
            <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
              The Trust Engine for youth who&apos;ve been counted out. Build trust. Earn freedom. Level up your life.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/register"
                className="group flex items-center gap-2 px-8 py-4 bg-fz-gold text-text-inverse font-semibold rounded-lg hover:bg-fz-gold-bright transition-all"
              >
                GET IN <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                to="/login"
                className="px-8 py-4 border border-fz-border text-text-primary font-medium rounded-lg hover:bg-fz-elevated transition-all"
              >
                ALREADY IN? SIGN IN
              </Link>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.2 }} className="mt-16">
            <ChevronDown className="w-6 h-6 mx-auto text-text-muted animate-bounce" />
          </motion.div>
        </div>
      </section>

      {/* HOW FLOWQUEST WORKS */}
      <section className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            custom={0}
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display text-4xl md:text-5xl text-fz-gold mb-4">HOW FLOWQUEST WORKS</h2>
            <p className="text-text-secondary max-w-xl mx-auto">Three steps. No fluff. Just real progress.</p>
          </motion.div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Zap,
                title: "VIBE CHECK",
                desc: "Check in. Pick your mood. Get matched with your Character.",
                color: "text-fz-blue",
                border: "border-fz-blue/30",
              },
              {
                icon: Flame,
                title: "THE DUMP",
                desc: "Vent it all. Voice or text. No filters. Your Character listens.",
                color: "text-fz-gold",
                border: "border-fz-gold/30",
              },
              {
                icon: Target,
                title: "TACTICAL ACTION",
                desc: "Walk away with one thing to do. One step forward.",
                color: "text-tier-flex",
                border: "border-tier-flex/30",
              },
            ].map((step, i) => (
              <motion.div
                key={step.title}
                custom={i + 1}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                className={`p-8 rounded-2xl bg-fz-elevated border ${step.border} hover:bg-fz-overlay transition-all group`}
              >
                <div className={`w-14 h-14 rounded-xl bg-fz-base flex items-center justify-center mb-6 ${step.color}`}>
                  <step.icon className="w-7 h-7" />
                </div>
                <h3 className={`font-display text-2xl mb-3 ${step.color}`}>{step.title}</h3>
                <p className="text-text-secondary leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* TRUST TIERS */}
      <section className="py-24 px-4 bg-fz-elevated">
        <div className="max-w-6xl mx-auto">
          <motion.div
            custom={0}
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display text-4xl md:text-5xl text-fz-gold mb-4">TRUST TIERS</h2>
            <p className="text-text-secondary max-w-xl mx-auto">Climb the ranks. Earn your freedom.</p>
          </motion.div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                name: "THE WATCH",
                threshold: 0,
                color: "#6366F1",
                desc: "Entry tier. Prove you're consistent. Check in daily.",
                features: ["Daily Vibe Checks", "Character Matching", "Basic Vouches"],
              },
              {
                name: "THE FLEX",
                threshold: 200,
                color: "#10B981",
                desc: "Mid tier. You've shown up. Now unlock real rewards.",
                features: ["Curfew Extensions", "Reduced Meetings", "Advanced Characters"],
              },
              {
                name: "THE VETTED",
                threshold: 500,
                color: "#D4AF37",
                desc: "Top tier. Full trust. Maximum autonomy unlocked.",
                features: ["Solo Pass", "Trust Premium", "Character Switch", "Mentor Bypass"],
              },
            ].map((tier, i) => (
              <motion.div
                key={tier.name}
                custom={i + 1}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                className="p-8 rounded-2xl bg-fz-base border border-fz-border hover:border-fz-gold/50 transition-all"
              >
                <div className="w-full h-1 rounded-full mb-6" style={{ backgroundColor: tier.color }} />
                <h3 className="font-display text-3xl mb-2" style={{ color: tier.color }}>
                  {tier.name}
                </h3>
                <p className="text-fz-gold font-mono text-sm mb-4">{tier.threshold}+ TRUST POINTS</p>
                <p className="text-text-secondary mb-6">{tier.desc}</p>
                <ul className="space-y-2">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-text-secondary">
                      <Shield className="w-4 h-4 text-fz-gold" /> {f}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* TRUST ENGINE FORMULA */}
      <section className="py-24 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div custom={0} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            <h2 className="font-display text-4xl md:text-5xl text-fz-gold mb-4">THE TRUST ENGINE FORMULA</h2>
            <p className="text-text-secondary mb-12">Your score is calculated in real time. No mystery. No hidden numbers.</p>
          </motion.div>
          <motion.div
            custom={1}
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="p-8 md:p-12 rounded-3xl bg-fz-elevated border border-fz-border font-mono text-lg md:text-2xl"
          >
            <div className="flex flex-wrap items-center justify-center gap-2 md:gap-4">
              <span className="text-text-muted">(</span>
              <span className="text-fz-blue" title="Consistency: Consecutive check-ins">C</span>
              <span className="text-text-muted">+</span>
              <span className="text-fz-gold" title="Weight: Multiplier for hard days">W</span>
              <span className="text-text-muted">+</span>
              <span className="text-tier-flex" title="Honesty: Bonus for disclosing traps">H</span>
              <span className="text-text-muted">+</span>
              <span className="text-fz-purple" title="Regulation: Points for Tactical Resets">R</span>
              <span className="text-text-muted">+</span>
              <span className="text-fz-gold-bright" title="Mentor Vouch: Manually awarded">M</span>
              <span className="text-text-muted">−</span>
              <span className="text-safe-red" title="Penalty: Deducted for detected Masks">P</span>
              <span className="text-text-muted">)</span>
              <span className="text-text-muted">÷</span>
              <span className="text-text-secondary" title="Time: Days since first check-in">T</span>
            </div>
          </motion.div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
            {[
              { label: "C", desc: "Consistency", detail: "Consecutive daily check-ins", color: "text-fz-blue" },
              { label: "W", desc: "Weight", detail: "Multiplier for hard days (1.0–2.0x)", color: "text-fz-gold" },
              { label: "H", desc: "Honesty", detail: "+25 per trap disclosure", color: "text-tier-flex" },
              { label: "R", desc: "Regulation", detail: "+10 per Tactical Reset", color: "text-fz-purple" },
              { label: "M", desc: "Mentor Vouch", detail: "0–50 points per vouch", color: "text-fz-gold-bright" },
              { label: "P", desc: "Penalty", detail: "−10 to −50 per Mask", color: "text-safe-red" },
              { label: "T", desc: "Time", detail: "Days since first check-in", color: "text-text-secondary" },
            ].map((item) => (
              <div key={item.label} className="p-4 rounded-xl bg-fz-elevated border border-fz-border text-left">
                <span className={`font-mono text-xl font-bold ${item.color}`}>{item.label}</span>
                <p className="text-sm text-text-primary font-medium mt-1">{item.desc}</p>
                <p className="text-xs text-text-muted mt-1">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FOR MENTORS */}
      <section className="py-24 px-4 bg-fz-elevated">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div custom={0} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            <h2 className="font-display text-4xl md:text-5xl text-fz-gold mb-4">FOR MENTORS</h2>
            <p className="text-text-secondary mb-8">Coach&apos;s view. Real data. Real impact.</p>
          </motion.div>
          <div className="grid md:grid-cols-3 gap-6 mb-10">
            {[
              { icon: Users, title: "Youth Roster", desc: "See every youth's trust score, Safe Harbor, and streak at a glance." },
              { icon: TrendingUp, title: "Trust Tracking", desc: "14-day score charts. Spot drops before they become crises." },
              { icon: Shield, title: "Safe Harbor Alerts", desc: "Automatic red/yellow flags when a youth needs attention." },
            ].map((item, i) => (
              <motion.div
                key={item.title}
                custom={i + 1}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                className="p-6 rounded-xl bg-fz-base border border-fz-border"
              >
                <item.icon className="w-8 h-8 text-fz-gold mb-4" />
                <h3 className="font-display text-xl mb-2">{item.title}</h3>
                <p className="text-text-secondary text-sm">{item.desc}</p>
              </motion.div>
            ))}
          </div>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 px-8 py-4 border border-fz-gold text-fz-gold font-medium rounded-lg hover:bg-fz-gold/10 transition-all"
          >
            JOIN AS MENTOR <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-12 px-4 border-t border-fz-border">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span className="font-display text-xl text-fz-gold">FLOWZONE</span>
            <span className="text-xs text-text-muted">Trust Engine v0.2.1</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-text-muted">
            <Link to="/login" className="hover:text-text-primary transition-colors">
              Sign In
            </Link>
            <Link to="/register" className="hover:text-text-primary transition-colors">
              Get In
            </Link>
            <span>Built for high-risk youth</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
