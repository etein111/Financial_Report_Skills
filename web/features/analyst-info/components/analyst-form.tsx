"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { createAnalystAction, getRegionsForSelectAction, updateAnalystAction } from "../actions";
import type { Analyst } from "../repo/analysts-repo";

export interface AnalystFormProps {
  open: boolean;
  analyst: Analyst | null;
  onClose: () => void;
  onSuccess: () => void;
}

type RegionOption = { id: string; name: string; code: string };

export function AnalystForm({ open, analyst, onClose, onSuccess }: AnalystFormProps) {
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [regions, setRegions] = React.useState<RegionOption[]>([]);
  const [fullName, setFullName] = React.useState(analyst?.full_name ?? "");
  const [chineseName, setChineseName] = React.useState(analyst?.chinese_name ?? "");
  const [email, setEmail] = React.useState(analyst?.email ?? "");
  const [regionId, setRegionId] = React.useState(analyst?.region_id ?? "");
  const [suffix, setSuffix] = React.useState(analyst?.suffix ?? "");
  const [sfc, setSfc] = React.useState(analyst?.sfc ?? "");
  const [isActive, setIsActive] = React.useState(analyst?.is_active ?? true);

  // Load regions when modal opens
  React.useEffect(() => {
    if (open) {
      getRegionsForSelectAction().then((result) => {
        if (result.ok) {
          setRegions(result.data);
        } else {
          setError("Failed to load regions");
        }
      });
    }
  }, [open]);

  React.useEffect(() => {
    if (analyst) {
      setFullName(analyst.full_name);
      setChineseName(analyst.chinese_name ?? "");
      setEmail(analyst.email);
      setRegionId(analyst.region_id ?? "");
      setSuffix(analyst.suffix ?? "");
      setSfc(analyst.sfc ?? "");
      setIsActive(analyst.is_active);
    } else {
      setFullName("");
      setChineseName("");
      setEmail("");
      setRegionId("");
      setSuffix("");
      setSfc("");
      setIsActive(true);
    }
    setError(null);
  }, [analyst, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const data = {
      full_name: fullName,
      chinese_name: chineseName || undefined,
      email,
      region_id: regionId,
      suffix: suffix || undefined,
      sfc: sfc || undefined,
      is_active: isActive,
    };

    const result = analyst
      ? await updateAnalystAction(analyst.id, data)
      : await createAnalystAction(data);

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
      title={analyst ? "Edit Analyst" : "Create Analyst"}
      description={analyst ? "Update analyst information" : "Add a new analyst"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} isLoading={isLoading}>
            {analyst ? "Update" : "Create"}
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
          <label htmlFor="full_name" className="block text-sm font-medium text-zinc-300">
            Full Name <span className="text-red-400">*</span>
          </label>
          <Input
            id="full_name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="e.g., Zhang San"
            required
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="chinese_name" className="block text-sm font-medium text-zinc-300">
            Chinese Name
          </label>
          <Input
            id="chinese_name"
            type="text"
            value={chineseName}
            onChange={(e) => setChineseName(e.target.value)}
            placeholder="e.g., 张三"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="email" className="block text-sm font-medium text-zinc-300">
            Email <span className="text-red-400">*</span>
          </label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="e.g., zhangsan@example.com"
            required
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="region_id" className="block text-sm font-medium text-zinc-300">
            Region <span className="text-red-400">*</span>
          </label>
          <select
            id="region_id"
            value={regionId}
            onChange={(e) => setRegionId(e.target.value)}
            required
            disabled={isLoading}
            className="w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none"
          >
            <option value="">Select a region...</option>
            {regions.map((region) => (
              <option key={region.id} value={region.id}>
                {region.name} ({region.code})
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label htmlFor="suffix" className="block text-sm font-medium text-zinc-300">
            Suffix
          </label>
          <Input
            id="suffix"
            type="text"
            value={suffix}
            onChange={(e) => setSuffix(e.target.value)}
            placeholder="e.g., CFA"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="sfc" className="block text-sm font-medium text-zinc-300">
            SFC
          </label>
          <Input
            id="sfc"
            type="text"
            value={sfc}
            onChange={(e) => setSfc(e.target.value)}
            placeholder="e.g., 12345678"
            disabled={isLoading}
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            id="is_active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            disabled={isLoading}
            className="h-4 w-4 rounded border-white/10 bg-zinc-800 text-blue-600 focus:ring-2 focus:ring-blue-500"
          />
          <label htmlFor="is_active" className="text-sm font-medium text-zinc-300">
            Active
          </label>
        </div>
      </form>
    </Modal>
  );
}
