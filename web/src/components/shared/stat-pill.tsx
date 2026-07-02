type StatTone = "neutral" | "green" | "yellow" | "blue";

const TONE_CLASS: Record<StatTone, string> = {
  neutral: "tag-pill bg-[var(--surface-muted)] text-[var(--muted)]",
  green: "tag-pill tag-green",
  yellow: "tag-pill tag-yellow",
  blue: "tag-pill tag-blue",
};

export function StatPill({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  tone?: StatTone;
}) {
  return (
    <div className="text-right">
      <p className="text-[0.65rem] uppercase tracking-wider text-[var(--muted)]">{label}</p>
      <p className={`mt-1 inline-flex ${TONE_CLASS[tone]}`}>{value}</p>
    </div>
  );
}
