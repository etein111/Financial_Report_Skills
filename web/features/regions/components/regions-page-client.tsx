"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  THead,
  TH,
  TR,
  TD,
} from "@/components/ui/table";
import { cn } from "@/lib/cn";
import { deleteRegionAction } from "../actions";
import type { Region } from "../repo/regions-repo";
import { RegionForm } from "./region-form";

export interface RegionsPageClientProps {
  regions: Region[];
  total: number;
  page: number;
  totalPages: number;
  currentQuery: string | null;
}

export function RegionsPageClient({
  regions,
  total,
  page,
  totalPages,
  currentQuery,
}: RegionsPageClientProps) {
  const router = useRouter();
  const [query, setQuery] = React.useState(currentQuery ?? "");
  const [deleteConfirmId, setDeleteConfirmId] = React.useState<string | null>(null);
  const [formModalOpen, setFormModalOpen] = React.useState(false);
  const [editingRegion, setEditingRegion] = React.useState<Region | null>(null);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (query) params.set("query", query);
    params.set("page", "1");
    router.push(`/regions?${params.toString()}`);
  };

  const handleDelete = async (id: string) => {
    const result = await deleteRegionAction(id);
    if (result.ok) {
      router.refresh();
    } else {
      alert(`Failed to delete region: ${result.error}`);
    }
  };

  const openCreateModal = () => {
    setEditingRegion(null);
    setFormModalOpen(true);
  };

  const openEditModal = (region: Region) => {
    setEditingRegion(region);
    setFormModalOpen(true);
  };

  const closeFormModal = () => {
    setFormModalOpen(false);
    setEditingRegion(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Regions</h1>
          <p className="text-sm text-zinc-400">
            Manage region data (total: {total})
          </p>
        </div>
        <Button onClick={openCreateModal}>Create Region</Button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <Input
          type="text"
          placeholder="Search by name or code..."
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
            <TH>Name</TH>
            <TH>Code</TH>
            <TH>Created At</TH>
            <TH className="text-right">Actions</TH>
          </TR>
        </THead>
        <tbody>
          {regions.map((region) => (
            <TR key={region.id}>
              <TD className="font-medium text-zinc-100">{region.name}</TD>
              <TD>
                <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-xs">
                  {region.code}
                </code>
              </TD>
              <TD className="text-zinc-400">
                {new Date(region.created_at).toLocaleString()}
              </TD>
              <TD className="text-right">
                {deleteConfirmId === region.id ? (
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
                      onClick={() => handleDelete(region.id)}
                    >
                      Confirm Delete
                    </Button>
                  </div>
                ) : (
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditModal(region)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirmId(region.id)}
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
                router.push(`/regions?${params.toString()}`);
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
                router.push(`/regions?${params.toString()}`);
              }}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Form Modal */}
      <RegionForm
        open={formModalOpen}
        region={editingRegion}
        onClose={closeFormModal}
        onSuccess={() => {
          closeFormModal();
          router.refresh();
        }}
      />
    </div>
  );
}
