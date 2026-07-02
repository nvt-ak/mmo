import type { DiscoveryJobResponse } from "@/lib/api/types";

interface DiscoveryProgressBarProps {
  progress: DiscoveryJobResponse;
}

function progressDetail(progress: DiscoveryJobResponse): string | null {
  const phase = progress.progress_phase;
  if (phase === "scan_videos" && progress.candidates_checked > 0) {
    return `${progress.candidates_checked} keywords checked`;
  }
  if (phase === "score_beta") {
    return `${progress.keywords_generated}/${progress.max_keywords ?? 10} saved`;
  }
  if (progress.keywords_generated > 0 && phase !== "complete") {
    return `${progress.keywords_generated}/${progress.max_keywords ?? 10} keywords`;
  }
  if (progress.videos_scanned > 0 && progress.candidates_checked === 0) {
    return `${progress.videos_scanned}/${progress.max_videos ?? 10} videos`;
  }
  return null;
}

export function DiscoveryProgressBar({ progress }: DiscoveryProgressBarProps) {
  const percent = Math.max(0, Math.min(100, progress.progress_percent ?? 0));
  const label = progress.progress_label || "Discovering…";
  const detail = progressDetail(progress);

  return (
    <div
      className="w-full min-w-[260px] rounded-md border border-(--border) bg-(--surface-muted)/60 px-3 py-2.5"
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={detail ? `${label} — ${detail}` : label}
    >
      <p className="text-xs leading-snug text-(--foreground)">{label}</p>
      {detail && (
        <p className="mt-0.5 text-[11px] text-(--muted)">{detail}</p>
      )}
      <div className="mt-2.5 flex items-center gap-2.5">
        <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-(--border)">
          <div
            className="h-full rounded-full bg-(--foreground) transition-[width] duration-300 ease-out"
            style={{ width: `${percent}%` }}
          />
        </div>
        <span className="w-8 shrink-0 text-right text-[11px] font-medium tabular-nums text-(--muted)">
          {percent}%
        </span>
      </div>
    </div>
  );
}
