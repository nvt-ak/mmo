export function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const tone =
    score >= 0.75 ? "bg-emerald-100 text-emerald-800" :
    score >= 0.5 ? "bg-amber-100 text-amber-800" :
    "bg-zinc-100 text-zinc-700";

  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${tone}`}>
      {pct}%
    </span>
  );
}
