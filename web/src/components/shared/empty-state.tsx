interface EmptyStateProps {
  title: string;
  description: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="panel-section px-6 py-14 text-center md:px-8 md:py-16">
      <p className="font-editorial text-xl text-(--foreground-strong)">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-(--muted)">{description}</p>
    </div>
  );
}
