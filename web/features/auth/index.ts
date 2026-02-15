export {
  requestPasswordResetAction,
  signInWithPasswordAction,
  signOutAction,
} from "./actions";

// Server-only exports - for use in Server Components only
export {
  getCurrentUser,
  getCurrentUserRole,
  requireAuth,
  requireAdmin,
} from "./server";

export { exchangeCodeForSession, verifyOtp } from "./server";
