"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ParticleField } from "@/components/particles/particle-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [errors, setErrors] = React.useState<{ email?: string; password?: string }>(
    {},
  );
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [forgotOpen, setForgotOpen] = React.useState(false);
  const [forgotEmail, setForgotEmail] = React.useState("");
  const [forgotSuccess, setForgotSuccess] = React.useState(false);
  const [forgotError, setForgotError] = React.useState<string | undefined>();

  function validate() {
    const next: typeof errors = {};
    if (!email.trim()) next.email = "Email is required";
    else if (!isValidEmail(email.trim())) next.email = "Invalid email format";
    if (!password) next.password = "Password is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    const delayMs = 1000 + Math.floor(Math.random() * 1001); // 1-2s
    await new Promise((r) => window.setTimeout(r, delayMs));

    // Prototype-only deterministic failure: password === "fail"
    if (password.trim().toLowerCase() === "fail") {
      setIsSubmitting(false);
      toast.error("Sign in failed (prototype simulation).", { title: "Error" });
      return;
    }

    router.push("/desktop");
  }

  function openForgotPassword() {
    setForgotEmail(email);
    setForgotSuccess(false);
    setForgotError(undefined);
    setForgotOpen(true);
  }

  function submitForgotPassword(e: React.FormEvent) {
    e.preventDefault();
    setForgotError(undefined);
    setForgotSuccess(false);

    if (!forgotEmail.trim()) {
      setForgotError("Email is required");
      return;
    }
    if (!isValidEmail(forgotEmail.trim())) {
      setForgotError("Invalid email format");
      return;
    }

    // Prototype-only: always show success (avoid email enumeration).
    setForgotSuccess(true);
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <ParticleField />

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-sm rounded-[12px] border border-white/10 bg-zinc-900/70 p-6 backdrop-blur-md">
          <div className="mb-6 space-y-2 text-center">
            <h1 className="text-2xl font-semibold text-zinc-50">
              The Future is Now
            </h1>
            <p className="text-sm text-zinc-400">
              Research Report Management System
            </p>
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
            />
            <Input
              label="Password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
            />

            <Button className="w-full" type="submit" isLoading={isSubmitting}>
              Login
            </Button>

            <div className="flex justify-center">
              <button
                type="button"
                className="text-sm text-zinc-300 underline decoration-white/30 underline-offset-4 hover:text-white"
                onClick={openForgotPassword}
              >
                Forgot password
              </button>
            </div>
          </form>
        </div>
      </div>

      <Modal
        open={forgotOpen}
        title="Reset password"
        description="Prototype only: no real email will be sent."
        onClose={() => setForgotOpen(false)}
        footer={
          <>
            <Button variant="ghost" type="button" onClick={() => setForgotOpen(false)}>
              Close
            </Button>
            <Button type="submit" form="forgot-form">
              Submit
            </Button>
          </>
        }
      >
        <form id="forgot-form" className="space-y-3" onSubmit={submitForgotPassword}>
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={forgotEmail}
            onChange={(e) => setForgotEmail(e.target.value)}
            error={forgotError}
          />
          {forgotSuccess ? (
            <p className="text-sm text-green-400">
              If this email exists, a reset link has been sent.
            </p>
          ) : (
            <p className="text-sm text-zinc-400">
              Enter your email address to receive a reset link.
            </p>
          )}
        </form>
      </Modal>
    </div>
  );
}

