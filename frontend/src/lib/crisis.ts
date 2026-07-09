/**
 * Crisis support resources shown in the "Get Help" panel.
 *
 * These are US national resources and are intentionally static so help is
 * always reachable, even if the backend is unavailable. If a managed resource
 * list is added later, this is the single place to swap the data source.
 */
export interface CrisisResource {
  /** Resource name shown as the heading. */
  name: string;
  /** Plain-language description of what the resource does. */
  description: string;
  /** Button label describing the action, e.g. "Call or text 988". */
  actionLabel: string;
  /** Actionable link (`tel:` / `sms:`). */
  href: string;
  /** Whether this is an immediate-danger / life-threatening resource. */
  urgent?: boolean;
}

export const CRISIS_RESOURCES: readonly CrisisResource[] = [
  {
    name: "988 Suicide & Crisis Lifeline",
    description:
      "Free, confidential support 24/7 for anyone in emotional distress or a suicidal crisis. Call or text.",
    actionLabel: "Call or text 988",
    href: "tel:988",
    urgent: true,
  },
  {
    name: "Crisis Text Line",
    description: "Text with a trained volunteer crisis counselor any time, day or night.",
    actionLabel: "Text HOME to 741741",
    href: "sms:741741&body=HOME",
  },
  {
    name: "Emergency services",
    description: "If you or someone else is in immediate danger, call 911 right now.",
    actionLabel: "Call 911",
    href: "tel:911",
    urgent: true,
  },
];

/**
 * Plain-language note about what FlowZone can and cannot do in a crisis.
 * Kept non-legalistic on purpose.
 */
export const CRISIS_DISCLAIMER =
  "FlowZone is not an emergency service and can't provide crisis care. If you're in danger or thinking about hurting yourself, please use one of the resources above — real people are ready to help.";
