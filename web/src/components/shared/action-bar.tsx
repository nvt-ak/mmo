interface ActionBarProps {
  count: number;
  label?: string;
  children: React.ReactNode;
}

export function ActionBar({ count, label = "selected", children }: ActionBarProps) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-(--border) bg-(--surface-muted) px-6 py-2.5 md:px-8">
      <span className="font-mono text-xs text-(--muted)">
        {count} {label}
      </span>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}
