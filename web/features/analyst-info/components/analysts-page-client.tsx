"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  THead,
  TH,
  TR,
  TD,
} from "@/components/ui/table";
import { cn } from "@/lib/cn";
import { deleteAnalystAction } from "../actions";
import type { Analyst } from "../repo/analysts-repo";
import { AnalystForm } from "./analyst-form";

export interface AnalystsPageClientProps {
  analysts: Analyst[];
  total: number;
  page: number;
  totalPages: number;
  currentQuery: string | null;
}

export function AnalystsPageClient({
  analysts,
  total,
  page,
  totalPages,
  currentQuery,
}: AnalystsPageClientProps) {
  const router = useRouter();
  const [query, setQuery] = React.useState(currentQuery ?? "");
  const [deleteConfirmId, setDeleteConfirmId] = React.useState<string | null>(null);
  const [formModalOpen, setFormModalOpen] = React.useState(false);
  const [editingAnalyst, setEditingAnalyst] = React.useState<Analyst | null>(null);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (query) params.set("query", query);
    params.set("page", "1");
    router.push(`/analyst-info?${params.toString()}`);
  };

  const handleDelete = async (id: string) => {
    const result = await deleteAnalystAction(id);
    if (result.ok) {
      router.refresh();
    } else {
      alert(`Failed to delete analyst: ${result.error}`);
    }
  };

  const openCreateModal = () => {
    setEditingAnalyst(null);
    setFormModalOpen(true);
  };

  const openEditModal = (analyst: Analyst) => {
    setEditingAnalyst(analyst);
    setFormModalOpen(true);
  };

  const closeFormModal = () => {
    setFormModalOpen(false);
    setEditingAnalyst(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Analyst Info</h1>
          <p className="text-sm text-zinc-400">
            Manage analyst information (total: {total})
          </p>
        </div>
        <Button onClick={openCreateModal}>Create Analyst</Button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <Input
          type="text"
          placeholder="Search by name or email..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-sm"
        />
        <Button type="submit">Search</Button>
      </form>

      {/* Table */}
      <Table>
        <THead>
          <TR>
            <TH>Full Name</TH>
            <TH>Chinese Name</TH>
            <TH>Email</TH>
            <TH>Region</TH>
            <TH>Status</TH>
            <TH className="text-right">Actions</TH>
          </TR>
        </THead>
        <tbody>
          {analysts.map((analyst) => (
            <TR key={analyst.id}>
              <TD className="font-medium text-zinc-100">{analyst.full_name}</TD>
              <TD className="text-zinc-400">{analyst.chinese_name || "-"}</TD>
              <TD className="text-zinc-300">{analyst.email}</TD>
              <TD>
                {analyst.region ? (
                  <span className="text-zinc-300">
                    {analyst.region.name} ({analyst.region.code})
                  </span>
                ) : (
                  <span className="text-zinc-500">-</span>
                )}
              </TD>
              <TD>
                {analyst.is_active ? (
                  <Badge variant="success">Active</Badge>
                ) : (
                  <Badge variant="secondary">Inactive</Badge>
                )}
              </TD>
              <TD className="text-right">
                {deleteConfirmId === analyst.id ? (
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirmId(null)}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDelete(analyst.id)}
                    >
                      Confirm Delete
                    </Button>
                  </div>
                ) : (
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditModal(analyst)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirmId(analyst.id)}
                    >
                      Delete
                    </Button>
                  </div>
                )}
              </TD>
            </TR>
          ))}
        </tbody>
      </Table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-zinc-400">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page === 1}
              onClick={() => {
                const params = new URLSearchParams();
                if (currentQuery) params.set("query", currentQuery);
                params.set("page", String(page - 1));
                router.push(`/analyst-info?${params.toString()}`);
              }}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page === totalPages}
              onClick={() => {
                const params = new URLSearchParams();
                if (currentQuery) params.set("query", currentQuery);
                params.set("page", String(page + 1));
                router.push(`/analyst-info?${params.toString()}`);
              }}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Form Modal */}
      <AnalystForm
        open={formModalOpen}
        analyst={editingAnalyst}
        onClose={closeFormModal}
        onSuccess={() => {
          closeFormModal();
          router.refresh();
        }}
      />
    </div>
  );
}
