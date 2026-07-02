"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api/client";
import type { ProfileStage } from "@/lib/api/types";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";

interface ProfilesPageProps {
  stage: ProfileStage;
}

export function ProfilesPage({ stage }: ProfilesPageProps) {
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const [handle, setHandle] = useState("");

  const queryKey = ["profiles", stage];

  const { data, isLoading, isError, error } = useQuery({
    queryKey,
    queryFn: () => api.listProfiles(stage),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["profiles"] });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createProfile({
        label: label.trim(),
        handle: handle.trim(),
        stage,
      }),
    onSuccess: () => {
      setLabel("");
      setHandle("");
      invalidate();
    },
  });

  const promoteMutation = useMutation({
    mutationFn: (id: string) => api.promoteProfile(id),
    onSuccess: invalidate,
  });

  const toggleEligibleMutation = useMutation({
    mutationFn: ({ id, beta_eligible }: { id: string; beta_eligible: boolean }) =>
      api.updateProfile(id, { beta_eligible }),
    onSuccess: invalidate,
  });

  const items = data?.items ?? [];
  const title = stage === "nurture" ? "Nurture profiles" : "Beta profiles";

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title={title}
        description={
          stage === "nurture"
            ? "TikTok accounts for trend clone posting. Tick ready for beta, then promote."
            : "Creator Rewards accounts — consume beta pool only."
        }
      />

      <div className="border-b border-(--border) px-8 py-4">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (label.trim() && handle.trim()) createMutation.mutate();
          }}
        >
          <label className="flex flex-col gap-1 text-xs text-(--muted)">
            Label
            <input
              className="field-input min-w-[160px]"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Account 1"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-(--muted)">
            Handle
            <input
              className="field-input min-w-[160px]"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              placeholder="@handle"
            />
          </label>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="btn btn-primary"
          >
            Add profile
          </button>
        </form>
      </div>

      <div className="flex-1 overflow-auto px-8 py-6">
        {isLoading && <p className="text-sm text-(--muted)">Loading profiles</p>}
        {isError && (
          <div className="surface-card border-(--pastel-red-bg) bg-(--pastel-red-bg) px-4 py-3 text-sm text-(--pastel-red-text)">
            {(error as Error).message}
          </div>
        )}
        {!isLoading && !isError && items.length === 0 && (
          <EmptyState title="No profiles" description="Add a TikTok account to get started." />
        )}
        {items.length > 0 && (
          <div className="surface-card overflow-hidden">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-(--border) bg-(--surface-muted) text-xs uppercase text-(--muted)">
                  <th className="px-4 py-3">Label</th>
                  <th className="px-4 py-3">Handle</th>
                  {stage === "nurture" && <th className="px-4 py-3">Beta ready</th>}
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.id} className="border-b border-(--border-subtle) last:border-b-0">
                    <td className="px-4 py-3.5 font-medium">{p.label}</td>
                    <td className="px-4 py-3.5 font-mono text-xs">@{p.handle.replace(/^@/, "")}</td>
                    {stage === "nurture" && (
                      <td className="px-4 py-3.5">
                        <input
                          type="checkbox"
                          checked={p.beta_eligible}
                          onChange={(e) =>
                            toggleEligibleMutation.mutate({
                              id: p.id,
                              beta_eligible: e.target.checked,
                            })
                          }
                        />
                      </td>
                    )}
                    <td className="px-4 py-3.5">
                      {stage === "nurture" && (
                        <button
                          type="button"
                          className="btn btn-secondary px-2 py-1 text-xs"
                          disabled={!p.beta_eligible || promoteMutation.isPending}
                          onClick={() => promoteMutation.mutate(p.id)}
                        >
                          Promote to beta
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
