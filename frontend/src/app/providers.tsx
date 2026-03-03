"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

type SupabaseBrowserClient = ReturnType<typeof createSupabaseBrowserClient>;

const SupabaseClientContext = createContext<SupabaseBrowserClient | null>(null);

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
  const supabaseClient = useMemo(() => createSupabaseBrowserClient(), []);

  return (
    <SupabaseClientContext.Provider value={supabaseClient}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </SupabaseClientContext.Provider>
  );
}
