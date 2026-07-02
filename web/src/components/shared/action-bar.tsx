interface ActionBarProps {
  count: number;
  label?: string;
  children: React.ReactNode;
}

export function ActionBar({ count, label = "selected", children }: ActionBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-[var(--border)] bg-[var(--surface-muted)] px-8 py-3">
      <span className="font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
        {count} {label}
      </span>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}
