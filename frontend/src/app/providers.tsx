"use client";

import { createBrowserClient } from "@supabase/ssr";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type SupabaseBrowserClient = ReturnType<typeof createBrowserClient>;

const SupabaseClientContext = createContext<SupabaseBrowserClient | null>(null);

function createSupabaseClient(): SupabaseBrowserClient {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  }

  return createBrowserClient(supabaseUrl, supabaseAnonKey);
}

export function useSupabaseClient(): SupabaseBrowserClient {
  const client = useContext(SupabaseClientContext);
  if (!client) {
    throw new Error("useSupabaseClient must be used within Providers");
  }
  return client;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
          },
        },
      })
  );
  const supabaseClient = useMemo(() => createSupabaseClient(), []);

  return (
    <SupabaseClientContext.Provider value={supabaseClient}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </SupabaseClientContext.Provider>
  );
}
