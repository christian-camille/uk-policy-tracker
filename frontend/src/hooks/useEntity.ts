"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useEntity(nodeId: number) {
  return useQuery({
    queryKey: ["entity", nodeId],
    queryFn: () => api.getEntity(nodeId),
    enabled: !!nodeId,
  });
}
