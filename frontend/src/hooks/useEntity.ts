"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface UseEntityOptions {
  nodeId?: number;
  entityType?: string;
  entityId?: number;
}

export function useEntity({ nodeId, entityType, entityId }: UseEntityOptions) {
  const hasNodeId = typeof nodeId === "number" && Number.isFinite(nodeId);
  const hasSourceLookup =
    typeof entityType === "string" &&
    entityType.length > 0 &&
    typeof entityId === "number" &&
    Number.isFinite(entityId);

  return useQuery({
    queryKey: ["entity", nodeId ?? null, entityType ?? null, entityId ?? null],
    queryFn: () => {
      if (hasSourceLookup) {
        return api.getEntityBySource(entityType, entityId);
      }
      if (hasNodeId) {
        return api.getEntity(nodeId);
      }
      throw new Error("Missing entity lookup parameters");
    },
    enabled: hasNodeId || hasSourceLookup,
  });
}
