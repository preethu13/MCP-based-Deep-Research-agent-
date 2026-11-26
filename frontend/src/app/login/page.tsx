"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { user, signInWithGoogle, isConfigured, authError } = useAuth();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      router.push("/");
    }
  }, [user, router]);

  const handleGoogleSignIn = async () => {
    if (!isConfigured) {
      setErrorMsg("Firebase credentials are not configured yet in .env.local.");
      return;
    }
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await signInWithGoogle();
      router.push("/");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to authenticate with Google.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full min-h-[calc(100vh-160px)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-surface-container rounded-2xl p-8 border border-surface-container-high/60 shadow-2xl flex flex-col gap-6">
        {/* Back Link */}
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-on-surface-variant hover:text-on-surface transition-colors w-fit"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>

        {/* Header */}
        <div className="flex flex-col items-center text-center gap-2">
          <div className="w-12 h-12 rounded-full bg-surface-container-high flex items-center justify-center shadow-inner border border-surface-container-highest">
            <span className="material-symbols-outlined text-primary text-[26px]">hub</span>
          </div>
          <h1 className="text-2xl font-bold text-on-surface tracking-tight mt-2">
            Welcome to Stitch MCP
          </h1>
          <p className="text-sm text-on-surface-variant max-w-xs">
            Sign in to access your autonomous research desk and saved sessions
          </p>
        </div>

        {/* Warning if Firebase not configured */}
        {!isConfigured && (
          <div className="bg-secondary/10 border border-secondary/30 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-secondary-fixed">
            <AlertCircle className="w-4 h-4 text-secondary shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-on-surface">Firebase Configuration Required</p>
              <p className="text-on-surface-variant mt-0.5 leading-relaxed">
                Add your Firebase project keys to <code className="bg-surface-container-high px-1 py-0.5 rounded text-secondary-fixed">.env.local</code> to enable Google sign-in.
              </p>
            </div>
          </div>
        )}

        {/* Error message */}
        {(errorMsg || authError) && (
          <div className="bg-error/10 border border-error/30 rounded-xl p-3 text-xs text-error flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg || authError}</span>
          </div>
        )}

        {/* Google Sign In Button */}
        <div className="flex flex-col gap-3 pt-2">
          <button
            onClick={handleGoogleSignIn}
            disabled={submitting}
            className="w-full h-12 rounded-xl bg-surface-container-highest hover:bg-surface-bright text-on-surface font-medium text-sm flex items-center justify-center gap-3 border border-surface-container-high/80 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60 shadow-md"
          >
            {/* Google SVG Icon */}
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>{submitting ? "Signing in..." : "Continue with Google"}</span>
          </button>
        </div>

        <p className="text-center text-[11px] text-on-surface-variant/70">
          Protected by Google Firebase Authentication. Your research records remain strictly private.
        </p>
      </div>
    </div>
  );
}
