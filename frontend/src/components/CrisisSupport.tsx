import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { LifeBuoy, Phone } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CRISIS_DISCLAIMER, CRISIS_RESOURCES } from "@/lib/crisis";

interface CrisisSupportContextValue {
  /** Open the crisis "Get Help" dialog from anywhere in the app. */
  openCrisisHelp: () => void;
  closeCrisisHelp: () => void;
}

const CrisisSupportContext = createContext<CrisisSupportContextValue | null>(null);

/**
 * Provides a single app-wide crisis "Get Help" dialog so any screen — the
 * navbar, Vibe Check storm state, FlowQuest, Safe Harbor panels — can surface
 * the same resources with one call. Mount once near the app root.
 */
export function CrisisSupportProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const value = useMemo<CrisisSupportContextValue>(
    () => ({
      openCrisisHelp: () => setOpen(true),
      closeCrisisHelp: () => setOpen(false),
    }),
    [],
  );

  return (
    <CrisisSupportContext.Provider value={value}>
      {children}
      <CrisisResourcesDialog open={open} onOpenChange={setOpen} />
    </CrisisSupportContext.Provider>
  );
}

export function useCrisisSupport(): CrisisSupportContextValue {
  const ctx = useContext(CrisisSupportContext);
  if (!ctx) throw new Error("useCrisisSupport must be used within CrisisSupportProvider");
  return ctx;
}

function CrisisResourcesDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-borderSubtle bg-bgElevated text-textPrimary sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-display text-2xl tracking-wide">
            <LifeBuoy className="h-6 w-6 text-brandGold" aria-hidden="true" />
            You&apos;re not alone
          </DialogTitle>
          <DialogDescription className="text-textSecondary">
            If things feel like too much right now, reach out. These are free, confidential, and
            available 24/7.
          </DialogDescription>
        </DialogHeader>

        <ul className="space-y-3">
          {CRISIS_RESOURCES.map((resource) => (
            <li
              key={resource.name}
              className={`rounded-fz-md border p-3 ${
                resource.urgent
                  ? "border-safeRed/40 bg-safeRed/5"
                  : "border-borderSubtle bg-bgOverlay"
              }`}
            >
              <p className="text-sm font-semibold text-textPrimary">{resource.name}</p>
              <p className="mt-0.5 text-xs text-textSecondary">{resource.description}</p>
              <a
                href={resource.href}
                className={`mt-2 inline-flex items-center gap-1.5 rounded-fz-sm px-3 py-1.5 text-sm font-medium transition-colors ${
                  resource.urgent
                    ? "bg-safeRed text-white hover:bg-safeRed/90"
                    : "bg-brandGold text-textInverse hover:bg-brandGoldBright"
                }`}
              >
                <Phone size={14} aria-hidden="true" />
                {resource.actionLabel}
              </a>
            </li>
          ))}
        </ul>

        <p className="text-xs leading-relaxed text-textMuted">{CRISIS_DISCLAIMER}</p>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Persistent "Get Help" affordance. Renders as a button that opens the shared
 * crisis dialog. `variant` controls presentation for different placements.
 */
export function GetHelpButton({
  variant = "nav",
  className = "",
}: {
  variant?: "nav" | "block";
  className?: string;
}) {
  const { openCrisisHelp } = useCrisisSupport();

  const handleClick = useCallback(() => openCrisisHelp(), [openCrisisHelp]);

  if (variant === "block") {
    return (
      <button
        onClick={handleClick}
        className={`inline-flex items-center justify-center gap-2 rounded-fz-md bg-safeRed px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-safeRed/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-safeRed ${className}`}
      >
        <LifeBuoy size={16} aria-hidden="true" />
        Get help now
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      aria-label="Get crisis help and support resources"
      className={`inline-flex items-center gap-1.5 rounded-fz-md border border-safeRed/40 px-2.5 py-1.5 text-sm font-medium text-safeRed transition-colors hover:bg-safeRed/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-safeRed ${className}`}
    >
      <LifeBuoy size={15} aria-hidden="true" />
      <span className="hidden sm:inline">Get Help</span>
    </button>
  );
}
