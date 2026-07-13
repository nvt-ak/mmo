interface TabBarProps<T extends string> {
  tabs: { value: T; label: string; count?: number }[];
  value: T;
  onChange: (value: T) => void;
}

export function TabBar<T extends string>({ tabs, value, onChange }: TabBarProps<T>) {
  return (
    <div className="flex flex-wrap gap-0 border-b border-(--border)" role="tablist">
      {tabs.map((tab) => {
        const active = tab.value === value;
        return (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.value)}
            className={`-mb-px min-h-[2.75rem] border-b-2 px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
              active
                ? "border-(--foreground-strong) text-(--foreground-strong)"
                : "border-transparent text-(--muted) hover:text-(--foreground)"
            }`}
          >
            {tab.label}
            {tab.count != null && (
              <span className="ml-2 font-mono text-xs text-(--muted)">{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
