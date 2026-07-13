export function StatPill({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  tone?: "neutral" | "green" | "yellow" | "blue";
}) {
  const toneClass =
    tone === "green"
      ? "tag-pill tag-green"
      : tone === "yellow"
        ? "tag-pill tag-yellow"
        : tone === "blue"
          ? "tag-pill tag-blue"
          : "tag-pill bg-(--surface-muted) text-(--muted)";

  return (
    <div>
      <p className="text-[0.65rem] font-medium text-(--muted)">{label}</p>
      <p className={`mt-1 inline-flex font-mono text-sm ${toneClass}`}>{value}</p>
    </div>
  );
}
