"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type User,
} from "firebase/auth";
import {
  getFirebaseAuth,
  googleProvider,
  isFirebaseConfigured,
} from "@/lib/firebase";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isConfigured: boolean;
  signInWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  authError: string | null;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  isConfigured: false,
  signInWithGoogle: async () => {},
  logout: async () => {},
  authError: null,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const authInstance = getFirebaseAuth();
    if (!authInstance) {
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(authInstance, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    const authInstance = getFirebaseAuth();
    if (!authInstance) {
      setAuthError("Firebase is not initialized. Please ensure your .env.local keys are loaded.");
      throw new Error("Firebase is not initialized.");
    }

    try {
      setAuthError(null);
      await signInWithPopup(authInstance, googleProvider);
    } catch (err: any) {
      console.error("Google sign-in error:", err);
      const code = err.code || "";
      const msg =
        code === "auth/popup-closed-by-user"
          ? "Sign-in popup was closed before completing."
          : code === "auth/unauthorized-domain"
          ? "Domain unauthorized. Add 'localhost' to Authorized Domains in Firebase Console -> Authentication -> Settings."
          : err.message || "Failed to sign in with Google.";
      setAuthError(msg);
      throw new Error(msg);
    }
  };

  const logout = async () => {
    const authInstance = getFirebaseAuth();
    if (!authInstance) return;
    try {
      await signOut(authInstance);
      setUser(null);
    } catch (err: any) {
      console.error("Sign-out error:", err);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isConfigured: isFirebaseConfigured,
        signInWithGoogle,
        logout,
        authError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
