interface PageHeaderProps {
  title: string;
  description?: string;
  meta?: React.ReactNode;
  toolbar?: React.ReactNode;
  tabs?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  meta,
  toolbar,
  tabs,
  actions,
}: PageHeaderProps) {
  return (
    <header className="shrink-0 border-b border-(--border) bg-(--surface) px-6 py-6 md:px-8">
      <div className="flex flex-wrap items-start justify-between gap-4 md:gap-6">
        <div className="min-w-0 flex-1" style={{ overflowWrap: "anywhere" }}>
          <h1 className="font-editorial text-2xl font-medium leading-tight text-(--foreground-strong) md:text-[1.75rem]">
            {title}
          </h1>
          {description && (
            <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-(--muted)">{description}</p>
          )}
          {meta && <div className="mt-4">{meta}</div>}
        </div>
        {(toolbar || actions) && (
          <div className="flex w-full min-w-0 flex-col items-stretch gap-3 sm:w-auto sm:flex-row sm:items-center sm:justify-end">
            {toolbar}
            {actions}
          </div>
        )}
      </div>
      {tabs && <div className="mt-5 -mb-px">{tabs}</div>}
    </header>
  );
}
