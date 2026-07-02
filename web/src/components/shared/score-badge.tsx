export function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const tone =
    score >= 0.75 ? "tag-green" :
    score >= 0.5 ? "tag-yellow" :
    "tag-pill bg-[var(--surface-muted)] text-[var(--muted)]";

  return <span className={`tag-pill ${tone}`}>{pct}%</span>;
}
