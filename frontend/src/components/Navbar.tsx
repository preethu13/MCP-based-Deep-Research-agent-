"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { LogOut } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const [health, setHealth] = useState<{ reachable: boolean; model: string } | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);

  const { user, logout } = useAuth();

  useEffect(() => {
    checkHealth()
      .then((res) => {
        setHealth({ reachable: res.llm_reachable, model: res.chat_model });
      })
      .catch(() => {
        setHealth({ reachable: false, model: "offline" });
      });

    const updateSession = () => {
      const id = typeof window !== "undefined" ? sessionStorage.getItem("active_research_session_id") : null;
      setActiveSessionId(id);
    };
    updateSession();
    window.addEventListener("active_session_change", updateSession);
    return () => window.removeEventListener("active_session_change", updateSession);
  }, [pathname]);

  const navLinks = [
    { label: "Home", href: "/" },
    { label: "Research", href: activeSessionId ? `/research?id=${activeSessionId}` : "/research" },
    { label: "Dashboard", href: "/dashboard" },
  ];

  return (
    <header className="fixed top-0 w-full z-50 bg-surface/80 backdrop-blur-xl border-b border-surface-container-high/40 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
      {/* Full width container: logo at far left, profile at far right */}
      <div className="h-16 w-full px-6 lg:px-10 flex items-center justify-between gap-space-md">
        {/* Brand / Logo at Far Left */}
        <div className="flex items-center gap-space-lg">
          <Link href="/" className="flex items-center gap-space-sm group">
            <div className="w-9 h-9 rounded-full bg-surface-container-high flex items-center justify-center p-space-xs shadow-[0_0_16px_-2px_rgba(99,102,241,0.5)]">
              <span className="material-symbols-outlined text-primary text-[20px]">hub</span>
            </div>
            <div className="flex flex-col">
              <span className="font-title-md text-title-md text-on-surface group-hover:text-primary transition-colors tracking-tight">
                Stitch MCP
              </span>
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant tracking-wider uppercase">
                Research Desk
              </span>
            </div>
          </Link>
        </div>

        {/* Center Pill Navigation */}
        <nav className="hidden md:flex items-center gap-space-xs bg-surface-container-low px-space-xs py-1 rounded-full border border-surface-container-high/30">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-space-md py-1.5 rounded-full font-label-ui text-label-ui transition-all ${
                  isActive
                    ? "bg-surface-container-highest text-on-surface shadow-sm font-semibold"
                    : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Actions / Profile at Far Right */}
        <div className="flex items-center gap-space-sm relative">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="flex items-center gap-2 p-1 rounded-full hover:bg-surface-container-high transition-colors focus:outline-none"
              >
                {user.photoURL ? (
                  <img
                    src={user.photoURL}
                    alt={user.displayName || "User"}
                    className="w-8 h-8 rounded-full border border-primary/40 object-cover"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold text-xs shadow-md shadow-primary/20">
                    {user.displayName ? user.displayName.charAt(0).toUpperCase() : "U"}
                  </div>
                )}
              </button>

              {/* Profile Dropdown */}
              {profileOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl bg-surface-container border border-surface-container-high/80 shadow-2xl p-2 z-50 flex flex-col gap-1">
                  <div className="px-3 py-2 border-b border-surface-container-high/40">
                    <p className="text-sm font-medium text-on-surface truncate">
                      {user.displayName || "Signed In"}
                    </p>
                    <p className="text-xs text-on-surface-variant truncate">
                      {user.email || ""}
                    </p>
                  </div>

                  <Link
                    href="/dashboard"
                    onClick={() => setProfileOpen(false)}
                    className="px-3 py-2 rounded-lg text-xs text-on-surface hover:bg-surface-container-high transition-colors"
                  >
                    Dashboard & Sessions
                  </Link>

                  <button
                    onClick={() => {
                      setProfileOpen(false);
                      logout();
                    }}
                    className="px-3 py-2 rounded-lg text-xs text-error hover:bg-error/10 flex items-center gap-2 transition-colors text-left"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link
              href="/login"
              className="px-4 py-1.5 rounded-full bg-surface-container-high hover:bg-surface-bright text-on-surface font-label-ui text-xs font-medium border border-surface-container-high flex items-center gap-1.5 transition-all shadow-sm"
            >
              <span className="material-symbols-outlined text-[16px] text-primary">login</span>
              <span>Sign In</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
