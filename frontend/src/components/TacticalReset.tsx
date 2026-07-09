import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Guided box-breathing grounding exercise ("Tactical Reset").
 *
 * This is a purely front-end self-help tool. It intentionally makes no claim
 * about affecting the trust score — score-affecting resets are owned by the
 * backend. It's a calm, offline-safe way to slow down in the moment.
 */

const PHASES = [
  { label: "Breathe in", seconds: 4 },
  { label: "Hold", seconds: 4 },
  { label: "Breathe out", seconds: 4 },
  { label: "Hold", seconds: 4 },
] as const;

const TOTAL_CYCLES = 4;

export default function TacticalReset({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const prefersReducedMotion = useReducedMotion();
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [cycle, setCycle] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState<number>(PHASES[0].seconds);
  const [done, setDone] = useState(false);
  const intervalRef = useRef<number | null>(null);

  // Reset state whenever the dialog opens.
  useEffect(() => {
    if (!open) return;
    setPhaseIndex(0);
    setCycle(0);
    setSecondsLeft(PHASES[0].seconds);
    setDone(false);
  }, [open]);

  // Drive the countdown while open and not finished.
  useEffect(() => {
    if (!open || done) return;

    intervalRef.current = window.setInterval(() => {
      setSecondsLeft((s) => {
        if (s > 1) return s - 1;

        // Advance to the next phase (and cycle) when a phase completes.
        setPhaseIndex((prevPhase) => {
          const nextPhase = (prevPhase + 1) % PHASES.length;
          if (nextPhase === 0) {
            setCycle((c) => {
              const nextCycle = c + 1;
              if (nextCycle >= TOTAL_CYCLES) setDone(true);
              return nextCycle;
            });
          }
          return nextPhase;
        });
        return PHASES[(phaseIndex + 1) % PHASES.length].seconds;
      });
    }, 1000);

    return () => {
      if (intervalRef.current !== null) window.clearInterval(intervalRef.current);
    };
  }, [open, done, phaseIndex]);

  const phase = PHASES[phaseIndex];
  const isInhale = phase.label === "Breathe in";
  const isExhale = phase.label === "Breathe out";
  const scale = prefersReducedMotion ? 1 : isInhale ? 1.25 : isExhale ? 0.75 : 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="border-borderSubtle bg-bgElevated text-textPrimary sm:max-w-sm"
      >
        <DialogHeader>
          <DialogTitle className="font-display text-2xl tracking-wide">Tactical Reset</DialogTitle>
          <DialogDescription className="text-textSecondary">
            {done
              ? "Nice work. Notice how your body feels now."
              : "Follow the circle. Four slow rounds of box breathing."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-6 py-4">
          {!done ? (
            <>
              <div className="relative flex h-44 w-44 items-center justify-center">
                <motion.div
                  className="absolute inset-0 rounded-full bg-brandGold/10"
                  animate={{ scale }}
                  transition={{ duration: prefersReducedMotion ? 0 : phase.seconds, ease: "easeInOut" }}
                />
                <div className="absolute inset-4 rounded-full border border-brandGold/40" />
                <div className="relative flex flex-col items-center">
                  <span className="font-display text-3xl tracking-wide text-brandGold">
                    {phase.label}
                  </span>
                  <span className="mt-1 font-mono text-4xl text-textPrimary">{secondsLeft}</span>
                </div>
              </div>
              <p className="text-xs text-textMuted">
                Round {Math.min(cycle + 1, TOTAL_CYCLES)} of {TOTAL_CYCLES}
              </p>
            </>
          ) : (
            <div className="flex h-44 w-44 items-center justify-center rounded-full bg-safeGreen/10">
              <span className="font-display text-2xl tracking-wide text-safeGreen">Reset done</span>
            </div>
          )}

          <button
            onClick={() => onOpenChange(false)}
            className="inline-flex items-center gap-2 rounded-fz-md border border-borderSubtle px-4 py-2 text-sm font-medium text-textSecondary transition-colors hover:text-textPrimary"
          >
            <X size={16} aria-hidden="true" />
            {done ? "Close" : "Stop"}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
