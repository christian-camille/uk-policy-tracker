"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  useMagicLinkLogin,
  useOAuthLogin,
  usePasswordLogin,
} from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const passwordLogin = usePasswordLogin();
  const magicLinkLogin = useMagicLinkLogin();
  const oauthLogin = useOAuthLogin();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [magicEmail, setMagicEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const onPasswordSubmit = (event: FormEvent) => {
    event.preventDefault();
    setMessage(null);
    passwordLogin.mutate(
      { email, password },
      {
        onSuccess: () => {
          router.push("/");
        },
        onError: () => {
          setMessage("Sign-in failed. Check your credentials and try again.");
        },
      }
    );
  };

  const onMagicLinkSubmit = (event: FormEvent) => {
    event.preventDefault();
    setMessage(null);
    magicLinkLogin.mutate(magicEmail, {
      onSuccess: () => {
        setMessage("Magic link sent. Check your inbox.");
      },
      onError: () => {
        setMessage("Could not send magic link. Try again.");
      },
    });
  };

  const onOAuthClick = (provider: "google" | "azure") => {
    setMessage(null);
    oauthLogin.mutate(provider, {
      onSuccess: (data: { url: string }) => {
        if (data.url) {
          window.location.href = data.url;
        }
      },
      onError: () => {
        setMessage("OAuth sign-in failed. Try again.");
      },
    });
  };

  return (
    <main className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Sign in</h1>
      <p className="text-sm text-gray-600 mb-6">
        Use your account to manage private topics and your dashboard.
      </p>

      {message && (
        <div className="mb-4 rounded-md border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
          {message}
        </div>
      )}

      <div className="space-y-6">
        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="text-base font-semibold text-gray-900 mb-3">Continue with OAuth</h2>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onOAuthClick("google")}
              className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black"
            >
              Google
            </button>
            <button
              type="button"
              onClick={() => onOAuthClick("azure")}
              className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black"
            >
              Microsoft
            </button>
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="text-base font-semibold text-gray-900 mb-3">Email + Password</h2>
          <form onSubmit={onPasswordSubmit} className="space-y-3">
            <input
              type="email"
              value={email}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setEmail(event.target.value)
              }
              placeholder="Email"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              required
            />
            <input
              type="password"
              value={password}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setPassword(event.target.value)
              }
              placeholder="Password"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              required
            />
            <button
              type="submit"
              disabled={passwordLogin.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {passwordLogin.isPending ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="text-base font-semibold text-gray-900 mb-3">Magic Link</h2>
          <form onSubmit={onMagicLinkSubmit} className="space-y-3">
            <input
              type="email"
              value={magicEmail}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setMagicEmail(event.target.value)
              }
              placeholder="Email"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              required
            />
            <button
              type="submit"
              disabled={magicLinkLogin.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {magicLinkLogin.isPending ? "Sending..." : "Send magic link"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
