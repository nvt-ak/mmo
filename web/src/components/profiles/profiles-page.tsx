"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api/client";
import type { ProfileStage } from "@/lib/api/types";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";

interface ProfilesPageProps {
  stage: ProfileStage;
}

function mutationError(error: unknown): string {
  return error instanceof Error ? error.message : "Request failed";
}

export function ProfilesPage({ stage }: ProfilesPageProps) {
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const [handle, setHandle] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const queryKey = ["profiles", stage];

  const { data, isLoading, isError, error } = useQuery({
    queryKey,
    queryFn: () => api.listProfiles(stage),
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["profiles"] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      api.createProfile({
        label: label.trim(),
        handle: handle.trim(),
        stage,
      }),
    onSuccess: async () => {
      const savedHandle = handle.trim().replace(/^@/, "");
      setLabel("");
      setHandle("");
      setNotice(`Added @${savedHandle}`);
      await invalidate();
    },
    onError: () => setNotice(null),
  });

  const promoteMutation = useMutation({
    mutationFn: (id: string) => api.promoteProfile(id),
    onSuccess: async () => {
      setNotice("Promoted to beta — see Beta profiles in the sidebar.");
      await invalidate();
    },
  });

  const toggleEligibleMutation = useMutation({
    mutationFn: ({ id, beta_eligible }: { id: string; beta_eligible: boolean }) =>
      api.updateProfile(id, { beta_eligible }),
    onSuccess: async () => {
      setNotice(null);
      await invalidate();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProfile(id),
    onSuccess: async () => {
      setNotice("Profile removed.");
      await invalidate();
    },
  });

  const items = data?.items ?? [];
  const title = stage === "nurture" ? "Nurture profiles" : "Beta profiles";
  const actionError =
    (createMutation.isError && mutationError(createMutation.error)) ||
    (promoteMutation.isError && mutationError(promoteMutation.error)) ||
    (toggleEligibleMutation.isError && mutationError(toggleEligibleMutation.error)) ||
    (deleteMutation.isError && mutationError(deleteMutation.error)) ||
    null;

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title={title}
        description={
          stage === "nurture"
            ? "TikTok accounts for trend clone posting. Tick Beta ready, then promote."
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
            disabled={createMutation.isPending || !label.trim() || !handle.trim()}
            className="btn btn-primary"
          >
            {createMutation.isPending ? "Adding…" : "Add profile"}
          </button>
        </form>
        {stage === "nurture" && (
          <p className="mt-3 text-xs text-(--muted)">
            Promote moves the account to{" "}
            <Link href="/profiles/beta" className="underline hover:text-(--foreground)">
              Beta profiles
            </Link>
            . Bulk post from pool is not wired yet (R7c).
          </p>
        )}
      </div>

      <div className="flex-1 overflow-auto px-8 py-6">
        {notice && !actionError && (
          <div className="surface-card mb-4 border-(--pastel-green-bg) bg-(--pastel-green-bg) px-4 py-3 text-sm text-(--pastel-green-text)">
            {notice}
            {notice.includes("Beta profiles") && (
              <>
                {" "}
                <Link href="/profiles/beta" className="font-medium underline">
                  Open beta list
                </Link>
              </>
            )}
          </div>
        )}
        {actionError && (
          <div className="surface-card mb-4 border-(--pastel-red-bg) bg-(--pastel-red-bg) px-4 py-3 text-sm text-(--pastel-red-text)">
            {actionError}
          </div>
        )}
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
                          disabled={toggleEligibleMutation.isPending}
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
                      <div className="flex flex-wrap gap-2">
                        {stage === "nurture" && (
                          <button
                            type="button"
                            className="btn btn-secondary px-2 py-1 text-xs"
                            disabled={!p.beta_eligible || promoteMutation.isPending}
                            title={
                              p.beta_eligible
                                ? "Move to beta profiles list"
                                : "Tick Beta ready first"
                            }
                            onClick={() => promoteMutation.mutate(p.id)}
                          >
                            Promote to beta
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-secondary px-2 py-1 text-xs"
                          disabled={deleteMutation.isPending}
                          onClick={() => {
                            if (window.confirm(`Remove ${p.label}?`)) {
                              deleteMutation.mutate(p.id);
                            }
                          }}
                        >
                          Remove
                        </button>
                      </div>
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
