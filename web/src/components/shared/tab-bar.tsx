interface TabBarProps<T extends string> {
  tabs: { value: T; label: string; count?: number }[];
  value: T;
  onChange: (value: T) => void;
}

export function TabBar<T extends string>({ tabs, value, onChange }: TabBarProps<T>) {
  return (
    <div className="flex flex-wrap gap-1 border-b border-[var(--border)]">
      {tabs.map((tab) => {
        const active = tab.value === value;
        return (
          <button
            key={tab.value}
            type="button"
            onClick={() => onChange(tab.value)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              active
                ? "border-[var(--foreground-strong)] text-[var(--foreground-strong)]"
                : "border-transparent text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {tab.label}
            {tab.count != null && (
              <span className="ml-2 font-mono text-xs text-[var(--muted)]">{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
