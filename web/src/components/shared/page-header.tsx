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
    <header className="relative z-10 border-b border-(--border) bg-(--surface) px-8 py-8">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0 flex-1">
          <h1 className="font-editorial text-3xl font-medium leading-tight text-(--foreground-strong)">
            {title}
          </h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm text-(--muted)">{description}</p>
          )}
          {meta && <div className="mt-4">{meta}</div>}
        </div>
        {(toolbar || actions) && (
          <div className="flex flex-row-reverse items-center gap-3">
            {toolbar}
            {actions}
          </div>
        )}
      </div>
      {tabs && <div className="mt-6">{tabs}</div>}
    </header>
  );
}
