"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { createRegionAction, updateRegionAction } from "../actions";
import type { Region } from "../repo/regions-repo";

export interface RegionFormProps {
  open: boolean;
  region: Region | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function RegionForm({ open, region, onClose, onSuccess }: RegionFormProps) {
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [name, setName] = React.useState(region?.name ?? "");
  const [code, setCode] = React.useState(region?.code ?? "");

  React.useEffect(() => {
    if (region) {
      setName(region.name);
      setCode(region.code);
    } else {
      setName("");
      setCode("");
    }
    setError(null);
  }, [region, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const result = region
      ? await updateRegionAction(region.id, { name, code })
      : await createRegionAction({ name, code });

    if (result.ok) {
      onSuccess();
    } else {
      setError(result.error);
      setIsLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title={region ? "Edit Region" : "Create Region"}
      description={region ? "Update region information" : "Add a new region"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} isLoading={isLoading}>
            {region ? "Update" : "Create"}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-md bg-red-900/20 border border-red-500/50 p-3">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="name" className="block text-sm font-medium text-zinc-300">
            Name <span className="text-red-400">*</span>
          </label>
          <Input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., China"
            required
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="code" className="block text-sm font-medium text-zinc-300">
            Code <span className="text-red-400">*</span>
          </label>
          <Input
            id="code"
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="e.g., CN"
            required
            disabled={isLoading}
          />
        </div>
      </form>
    </Modal>
  );
}
