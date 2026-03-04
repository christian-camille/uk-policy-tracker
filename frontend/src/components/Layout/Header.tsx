"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useCurrentUser, useLogout } from "@/hooks/useAuth";

export function Header() {
  const router = useRouter();
  const { data } = useCurrentUser();
  const logoutMutation = useLogout();
  const user = data?.user;

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-gray-900">
          GOV Tracker
        </Link>
        <nav className="flex gap-4 text-sm text-gray-600">
          <Link href="/" className="hover:text-gray-900">
            Watchlist
          </Link>
          {user ? (
            <>
              <span className="text-gray-500">{user.email ?? "Signed in"}</span>
              <button
                type="button"
                onClick={() => {
                  logoutMutation.mutate(undefined, {
                    onSuccess: () => {
                      router.push("/login");
                    },
                  });
                }}
                className="hover:text-gray-900"
              >
                {logoutMutation.isPending ? "Signing out..." : "Sign out"}
              </button>
            </>
          ) : (
            <Link href="/login" className="hover:text-gray-900">
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
