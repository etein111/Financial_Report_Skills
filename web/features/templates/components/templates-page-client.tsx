"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ActionButton } from "@/components/ui/action-button";
import { Button } from "@/components/ui/button";
import { ConfirmModal } from "@/components/ui/confirm-modal";
import { FileDropzone } from "@/components/ui/file-dropzone";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { formatShanghaiYmd } from "@/lib/time";
import { createBrowserClient } from "@/lib/supabase/browser";
import {
  activateTemplateAction,
  createTemplateAction,
  deleteTemplateAction,
} from "../actions";
import type {
  TemplateGroup,
  ReportType,
  FileType,
} from "../repo/templates-repo";

export interface TemplatesPageClientProps {
  templateGroups: TemplateGroup[];
}

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  company: "Company",
  sector: "Sector",
  company_flash: "Company Flash",
  sector_flash: "Sector Flash",
  common: "Common",
};

const FILE_TYPE_LABELS: Record<FileType, string> = {
  word: "Word",
  excel: "Excel",
};

export function TemplatesPageClient({
  templateGroups,
}: TemplatesPageClientProps) {
  const router = useRouter();
  const toast = useToast();

  // Upload modal
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [uploadReportType, setUploadReportType] =
    React.useState<ReportType>("company");
  const [uploadFileType, setUploadFileType] = React.useState<FileType>("word");
  const [uploadName, setUploadName] = React.useState("");
  const [uploadFile, setUploadFile] = React.useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = React.useState(false);
  const [uploadErrors, setUploadErrors] = React.useState<
    Record<string, string>
  >({});

  // Delete confirm
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [deleteId, setDeleteId] = React.useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = React.useState(false);

  function openUpload(reportType?: ReportType, fileType?: FileType) {
    setUploadReportType(reportType ?? "company");
    setUploadFileType(fileType ?? "word");
    setUploadName("");
    setUploadFile(null);
    setUploadErrors({});
    setUploadOpen(true);
  }

  async function submitUpload(e: React.FormEvent) {
    e.preventDefault();

    const name = uploadName.trim();
    if (!name) {
      setUploadErrors({ name: "Name is required" });
      return;
    }
    if (!uploadFile) {
      setUploadErrors({ file: "File is required" });
      return;
    }

    // Validate file type
    const validExtensions =
      uploadFileType === "word" ? [".docx", ".doc"] : [".xlsx", ".xls"];
    const fileExt = uploadFile.name
      .toLowerCase()
      .slice(uploadFile.name.lastIndexOf("."));
    if (!validExtensions.includes(fileExt)) {
      setUploadErrors({
        file: `Invalid file type. Expected ${validExtensions.join(" or ")}`,
      });
      return;
    }

    setUploadLoading(true);
    setUploadErrors({});

    try {
      const supabase = createBrowserClient();
      const safeName = uploadFile.name.replace(/[^a-zA-Z0-9._-]/g, "_");
      const filePath = `templates/${uploadReportType}/${uploadFileType}/${Date.now()}_${safeName}`;

      const { error: uploadError } = await supabase.storage
        .from("templates")
        .upload(filePath, uploadFile, { upsert: false });

      if (uploadError) {
        toast.error(uploadError.message, { title: "Error" });
        setUploadLoading(false);
        return;
      }

      const res = await createTemplateAction({
        name,
        report_type: uploadReportType,
        file_type: uploadFileType,
        file_path: filePath,
      });

      if (!res.ok) {
        toast.error(res.error, { title: "Error" });
        setUploadLoading(false);
        return;
      }

      setUploadOpen(false);
      toast.success("Template uploaded and activated.", { title: "Success" });
      router.refresh();
    } catch {
      toast.error("Failed to upload template", { title: "Error" });
    } finally {
      setUploadLoading(false);
    }
  }

  async function handleActivate(templateId: string) {
    const res = await activateTemplateAction(templateId);
    if (!res.ok) {
      toast.error(res.error, { title: "Error" });
      return;
    }
    toast.success("Template activated.", { title: "Success" });
    router.refresh();
  }

  function openDelete(templateId: string) {
    setDeleteId(templateId);
    setDeleteOpen(true);
  }

  async function confirmDelete() {
    if (!deleteId) return;

    setDeleteLoading(true);
    const res = await deleteTemplateAction(deleteId);
    setDeleteLoading(false);

    if (!res.ok) {
      toast.error(res.error, { title: "Error" });
      return;
    }

    setDeleteOpen(false);
    toast.success("Template deleted.", { title: "Success" });
    router.refresh();
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-zinc-900/60 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="text-xl font-semibold text-zinc-50">Templates</div>
          <Button onClick={() => openUpload()}>Upload Template</Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        {templateGroups.length === 0 ? (
          <div className="rounded-lg border border-white/10 bg-zinc-800/30 p-8 text-center">
            <p className="text-zinc-400">No templates uploaded yet.</p>
            <Button className="mt-4" onClick={() => openUpload()}>
              Upload First Template
            </Button>
          </div>
        ) : (
          templateGroups.map((group) => (
            <div
              key={`${group.report_type}-${group.file_type}`}
              className="rounded-lg border border-white/10 bg-zinc-800/30"
            >
              <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                <div>
                  <span className="font-medium text-zinc-100">
                    {REPORT_TYPE_LABELS[group.report_type as ReportType]}
                  </span>
                  <span className="mx-2 text-zinc-500">/</span>
                  <span className="text-zinc-300">
                    {FILE_TYPE_LABELS[group.file_type as FileType]}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  onClick={() =>
                    openUpload(
                      group.report_type as ReportType,
                      group.file_type as FileType,
                    )
                  }
                  className="text-xs px-2 py-1"
                >
                  Upload New Version
                </Button>
              </div>

              {/* Active template */}
              {group.active_template ? (
                <div className="border-b border-white/5 bg-green-500/5 px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="inline-flex items-center rounded bg-green-500/20 px-2 py-0.5 text-xs font-medium text-green-300">
                        Active
                      </span>
                      <span className="text-zinc-100">
                        {group.active_template.name}
                      </span>
                      <span className="text-sm text-zinc-400">
                        v{group.active_template.version}
                      </span>
                      <span className="text-sm text-zinc-500">
                        Uploaded{" "}
                        {formatShanghaiYmd(group.active_template.created_at)}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <ActionButton
                        onClick={() => openDelete(group.active_template!.id)}
                      >
                        Delete
                      </ActionButton>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="border-b border-white/5 px-4 py-3 text-zinc-400">
                  No active template
                </div>
              )}

              {/* History versions */}
              {group.history.length > 0 && (
                <div className="divide-y divide-white/5">
                  {group.history.map((template) => (
                    <div
                      key={template.id}
                      className="flex items-center justify-between px-4 py-2 hover:bg-white/5"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-zinc-300">{template.name}</span>
                        <span className="text-sm text-zinc-500">
                          v{template.version}
                        </span>
                        <span className="text-sm text-zinc-500">
                          {formatShanghaiYmd(template.created_at)}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <ActionButton
                          onClick={() => handleActivate(template.id)}
                        >
                          Activate
                        </ActionButton>
                        <ActionButton
                          tone="danger"
                          onClick={() => openDelete(template.id)}
                        >
                          Delete
                        </ActionButton>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </main>

      <Modal
        open={uploadOpen}
        title="Upload Template"
        onClose={() => setUploadOpen(false)}
        footer={
          <>
            <Button
              variant="ghost"
              type="button"
              onClick={() => setUploadOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" form="upload-form" isLoading={uploadLoading}>
              Upload
            </Button>
          </>
        }
      >
        <form id="upload-form" className="space-y-3" onSubmit={submitUpload}>
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Report Type"
              value={uploadReportType}
              onChange={(e) =>
                setUploadReportType(e.target.value as ReportType)
              }
              options={[
                { value: "company", label: "Company" },
                { value: "sector", label: "Sector" },
                { value: "company_flash", label: "Company Flash" },
                { value: "sector_flash", label: "Sector Flash" },
                { value: "common", label: "Common" },
              ]}
            />
            <Select
              label="File Type"
              value={uploadFileType}
              onChange={(e) => setUploadFileType(e.target.value as FileType)}
              options={[
                { value: "word", label: "Word (.docx)" },
                { value: "excel", label: "Excel (.xlsx)" },
              ]}
            />
          </div>
          <Input
            label="Template Name"
            placeholder="e.g., Company Report Template v1"
            value={uploadName}
            onChange={(e) => setUploadName(e.target.value)}
            error={uploadErrors.name}
          />
          <div className="space-y-1.5">
            <FileDropzone
              label="File"
              accept={uploadFileType === "word" ? ".docx,.doc" : ".xlsx,.xls"}
              file={uploadFile}
              onFileChange={setUploadFile}
              error={uploadErrors.file}
              hint={
                uploadFileType === "word"
                  ? "Supports .doc/.docx"
                  : "Supports .xls/.xlsx"
              }
            />
          </div>
          <p className="text-sm text-zinc-400">
            The uploaded template will be automatically activated.
          </p>
        </form>
      </Modal>

      <ConfirmModal
        open={deleteOpen}
        title="Delete template?"
        description="This action cannot be undone. Active templates cannot be deleted."
        onClose={() => setDeleteOpen(false)}
        onConfirm={confirmDelete}
        confirmTone="danger"
        confirmLabel="Delete"
        loading={deleteLoading}
      />
    </div>
  );
}
