interface EmptyStateProps {
  title: string;
  description: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="surface-card animate-fade-rise px-8 py-16 text-center">
      <p className="font-editorial text-xl text-(--foreground-strong)">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-(--muted)">{description}</p>
    </div>
  );
}
