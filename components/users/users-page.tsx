"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";
import {
  filterUsers,
  makeMockUsers,
  MockUser,
  paginate,
  UserRole,
  UserStatus,
} from "@/lib/mock/users";

const PAGE_SIZE = 12;

function formatDate(iso: string) {
  const d = new Date(iso);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function roleTone(role: UserRole) {
  if (role === "admin") return "blue";
  if (role === "sa") return "amber";
  return "zinc";
}

function statusTone(status: UserStatus) {
  return status === "active" ? "green" : "red";
}

export function UsersPage() {
  const toast = useToast();

  const [users, setUsers] = React.useState<MockUser[]>(() => makeMockUsers());
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(1);

  const filtered = React.useMemo(() => filterUsers(users, query), [users, query]);
  const paged = React.useMemo(
    () => paginate(filtered, page, PAGE_SIZE),
    [filtered, page],
  );

  React.useEffect(() => {
    setPage(1);
  }, [query]);

  // Invite modal
  const [inviteOpen, setInviteOpen] = React.useState(false);
  const [inviteEmail, setInviteEmail] = React.useState("");
  const [inviteRole, setInviteRole] = React.useState<UserRole>("analyst");
  const [inviteErrors, setInviteErrors] = React.useState<{ email?: string }>({});
  const [inviteLoading, setInviteLoading] = React.useState(false);

  // Edit modal
  const [editOpen, setEditOpen] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editEmail, setEditEmail] = React.useState("");
  const [editName, setEditName] = React.useState("");
  const [editErrors, setEditErrors] = React.useState<{ email?: string; name?: string }>(
    {},
  );

  // Change role
  const [roleOpen, setRoleOpen] = React.useState(false);
  const [roleId, setRoleId] = React.useState<string | null>(null);
  const [roleValue, setRoleValue] = React.useState<UserRole>("analyst");

  // Ban/Unban confirm
  const [banOpen, setBanOpen] = React.useState(false);
  const [banId, setBanId] = React.useState<string | null>(null);

  // Reset password
  const [resetOpen, setResetOpen] = React.useState(false);
  const [resetId, setResetId] = React.useState<string | null>(null);
  const [newPassword, setNewPassword] = React.useState("");
  const [resetError, setResetError] = React.useState<string | undefined>();

  // Delete confirm
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [deleteId, setDeleteId] = React.useState<string | null>(null);

  function openInvite() {
    setInviteEmail("");
    setInviteRole("analyst");
    setInviteErrors({});
    setInviteOpen(true);
  }

  async function submitInvite(e: React.FormEvent) {
    e.preventDefault();
    const next: { email?: string } = {};
    if (!inviteEmail.trim()) next.email = "Email is required";
    else if (!isValidEmail(inviteEmail.trim())) next.email = "Invalid email format";
    else if (
      users.some((u) => u.email.toLowerCase() === inviteEmail.trim().toLowerCase())
    )
      next.email = "Email already exists";

    setInviteErrors(next);
    if (Object.keys(next).length) return;

    setInviteLoading(true);
    await new Promise((r) => window.setTimeout(r, 600));

    const createdAt = new Date().toISOString();
    const user: MockUser = {
      id: `u_${crypto.randomUUID().slice(0, 8)}`,
      email: inviteEmail.trim(),
      name: inviteEmail.trim().split("@")[0],
      role: inviteRole,
      status: "active",
      createdAt,
    };

    setUsers((prev) => [user, ...prev]);
    setInviteLoading(false);
    setInviteOpen(false);
    toast.success("User invited (prototype).", { title: "Success" });
  }

  function openEdit(u: MockUser) {
    setEditingId(u.id);
    setEditEmail(u.email);
    setEditName(u.name);
    setEditErrors({});
    setEditOpen(true);
  }

  function submitEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editingId) return;

    const next: { email?: string; name?: string } = {};
    if (!editName.trim()) next.name = "Name is required";
    if (!editEmail.trim()) next.email = "Email is required";
    else if (!isValidEmail(editEmail.trim())) next.email = "Invalid email format";
    else if (
      users.some(
        (u) =>
          u.id !== editingId &&
          u.email.toLowerCase() === editEmail.trim().toLowerCase(),
      )
    )
      next.email = "Email already exists";

    setEditErrors(next);
    if (Object.keys(next).length) return;

    setUsers((prev) =>
      prev.map((u) =>
        u.id === editingId
          ? { ...u, email: editEmail.trim(), name: editName.trim() }
          : u,
      ),
    );
    setEditOpen(false);
    toast.success("User updated (prototype).", { title: "Success" });
  }

  function openChangeRole(u: MockUser) {
    setRoleId(u.id);
    setRoleValue(u.role);
    setRoleOpen(true);
  }

  function submitChangeRole(e: React.FormEvent) {
    e.preventDefault();
    if (!roleId) return;
    setUsers((prev) => prev.map((u) => (u.id === roleId ? { ...u, role: roleValue } : u)));
    setRoleOpen(false);
    toast.success("Role updated (prototype).", { title: "Success" });
  }

  function openBan(u: MockUser) {
    setBanId(u.id);
    setBanOpen(true);
  }

  function confirmBan() {
    if (!banId) return;
    setUsers((prev) =>
      prev.map((u) => {
        if (u.id !== banId) return u;
        const nextStatus: UserStatus = u.status === "active" ? "banned" : "active";
        return { ...u, status: nextStatus };
      }),
    );
    setBanOpen(false);
    toast.success("User status updated (prototype).", { title: "Success" });
  }

  function openReset(u: MockUser) {
    setResetId(u.id);
    setNewPassword("");
    setResetError(undefined);
    setResetOpen(true);
  }

  function submitReset(e: React.FormEvent) {
    e.preventDefault();
    setResetError(undefined);
    if (!newPassword.trim()) {
      setResetError("Password is required");
      return;
    }
    setResetOpen(false);
    toast.success("Password updated (prototype).", { title: "Success" });
  }

  function openDelete(u: MockUser) {
    setDeleteId(u.id);
    setDeleteOpen(true);
  }

  function confirmDelete() {
    if (!deleteId) return;
    setUsers((prev) => prev.filter((u) => u.id !== deleteId));
    setDeleteOpen(false);
    toast.success("User deleted (prototype).", { title: "Success" });
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-zinc-900/60 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="text-xl font-semibold text-zinc-50">Users</div>
          <Button onClick={openInvite}>Invite user</Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-6 py-8">
        <div className="flex items-end justify-between gap-4">
          <div className="w-full max-w-md">
            <Input
              label="Search"
              placeholder="Search by email or name"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="hidden text-sm text-zinc-400 sm:block">
            {paged.total} users
          </div>
        </div>

        <Table>
          <THead>
            <TR className="hover:bg-transparent">
              <TH>Email</TH>
              <TH>Role</TH>
              <TH>Status</TH>
              <TH>Created</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <tbody>
            {paged.items.length === 0 ? (
              <TR className="hover:bg-transparent">
                <TD colSpan={5} className="py-10 text-center text-zinc-400">
                  No users found
                </TD>
              </TR>
            ) : (
              paged.items.map((u) => (
                <TR key={u.id}>
                  <TD className="font-medium text-zinc-100">{u.email}</TD>
                  <TD>
                    <Badge tone={roleTone(u.role)}>{u.role.toUpperCase()}</Badge>
                  </TD>
                  <TD>
                    <Badge tone={statusTone(u.status)}>
                      {u.status === "active" ? "ACTIVE" : "BANNED"}
                    </Badge>
                  </TD>
                  <TD className="text-zinc-300">{formatDate(u.createdAt)}</TD>
                  <TD>
                    <div className="flex justify-end gap-2">
                      <ActionButton onClick={() => openEdit(u)}>Edit</ActionButton>
                      <ActionButton onClick={() => openChangeRole(u)}>
                        Role
                      </ActionButton>
                      <ActionButton onClick={() => openBan(u)}>
                        {u.status === "active" ? "Ban" : "Unban"}
                      </ActionButton>
                      <ActionButton onClick={() => openReset(u)}>
                        Reset PW
                      </ActionButton>
                      <ActionButton tone="danger" onClick={() => openDelete(u)}>
                        Delete
                      </ActionButton>
                    </div>
                  </TD>
                </TR>
              ))
            )}
          </tbody>
        </Table>

        <Pagination
          page={paged.page}
          totalPages={paged.totalPages}
          onChange={setPage}
        />
      </main>

      <Modal
        open={inviteOpen}
        title="Invite user"
        description="Prototype only. This will not send a real email."
        onClose={() => setInviteOpen(false)}
        footer={
          <>
            <Button variant="ghost" type="button" onClick={() => setInviteOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="invite-form" isLoading={inviteLoading}>
              Invite
            </Button>
          </>
        }
      >
        <form id="invite-form" className="space-y-3" onSubmit={submitInvite}>
          <Input
            label="Email"
            type="email"
            placeholder="user@example.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            error={inviteErrors.email}
          />

          <div className="space-y-1">
            <label className="text-sm font-medium text-zinc-300" htmlFor="invite-role">
              Role
            </label>
            <select
              id="invite-role"
              className="w-full rounded-[8px] border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500/50"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as UserRole)}
            >
              <option value="admin">Admin</option>
              <option value="sa">SA</option>
              <option value="analyst">Analyst</option>
            </select>
          </div>
        </form>
      </Modal>

      <Modal
        open={editOpen}
        title="Edit user"
        onClose={() => setEditOpen(false)}
        footer={
          <>
            <Button variant="ghost" type="button" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="edit-form">
              Save
            </Button>
          </>
        }
      >
        <form id="edit-form" className="space-y-3" onSubmit={submitEdit}>
          <Input
            label="Name"
            placeholder="Full name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            error={editErrors.name}
          />
          <Input
            label="Email"
            type="email"
            placeholder="user@example.com"
            value={editEmail}
            onChange={(e) => setEditEmail(e.target.value)}
            error={editErrors.email}
          />
        </form>
      </Modal>

      <Modal
        open={roleOpen}
        title="Change role"
        onClose={() => setRoleOpen(false)}
        footer={
          <>
            <Button variant="ghost" type="button" onClick={() => setRoleOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="role-form">
              Confirm
            </Button>
          </>
        }
      >
        <form id="role-form" className="space-y-3" onSubmit={submitChangeRole}>
          <div className="space-y-1">
            <label className="text-sm font-medium text-zinc-300" htmlFor="role-select">
              Role
            </label>
            <select
              id="role-select"
              className="w-full rounded-[8px] border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-2 focus:ring-blue-500/50"
              value={roleValue}
              onChange={(e) => setRoleValue(e.target.value as UserRole)}
            >
              <option value="admin">Admin</option>
              <option value="sa">SA</option>
              <option value="analyst">Analyst</option>
            </select>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={banOpen}
        title="Confirm"
        description="Update this user's status?"
        onClose={() => setBanOpen(false)}
        onConfirm={confirmBan}
      />

      <Modal
        open={resetOpen}
        title="Reset password"
        description="Prototype only. Password is not stored anywhere."
        onClose={() => setResetOpen(false)}
        footer={
          <>
            <Button variant="ghost" type="button" onClick={() => setResetOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" type="submit" form="reset-form">
              Reset
            </Button>
          </>
        }
      >
        <form id="reset-form" className="space-y-3" onSubmit={submitReset}>
          <Input
            label="New password"
            type="password"
            placeholder="••••••••"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            error={resetError}
          />
        </form>
      </Modal>

      <ConfirmModal
        open={deleteOpen}
        title="Delete user?"
        description="This action cannot be undone (prototype)."
        onClose={() => setDeleteOpen(false)}
        onConfirm={confirmDelete}
        confirmTone="danger"
        confirmLabel="Delete"
      />
    </div>
  );
}

function ActionButton({
  children,
  onClick,
  tone,
}: {
  children: React.ReactNode;
  onClick: () => void;
  tone?: "default" | "danger";
}) {
  return (
    <button
      type="button"
      className={cn(
        "rounded-[6px] border border-white/10 px-3 py-1 text-xs font-medium",
        "transition-colors duration-200",
        tone === "danger"
          ? "bg-red-600/20 text-red-100 hover:bg-red-600/30"
          : "bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between">
      <div className="text-sm text-zinc-400">
        Page {page} / {totalPages}
      </div>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Prev
        </Button>
        <Button
          variant="secondary"
          type="button"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

function ConfirmModal({
  open,
  title,
  description,
  onClose,
  onConfirm,
  confirmTone = "secondary",
  confirmLabel = "Confirm",
}: {
  open: boolean;
  title: string;
  description: string;
  onClose: () => void;
  onConfirm: () => void;
  confirmTone?: "secondary" | "danger";
  confirmLabel?: string;
}) {
  return (
    <Modal
      open={open}
      title={title}
      description={description}
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant={confirmTone === "danger" ? "danger" : "secondary"}
            type="button"
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-zinc-400">
        Please confirm to proceed (prototype).
      </p>
    </Modal>
  );
}

