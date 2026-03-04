"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useTopics(scope: "all" | "shared" | "private" = "all") {
  return useQuery({
    queryKey: ["topics", scope],
    queryFn: () => api.getTopics(scope),
  });
}

export function useCreateTopic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      label,
      searchQueries,
      isGlobal,
    }: {
      label: string;
      searchQueries: string[];
      isGlobal: boolean;
    }) => api.createTopic(label, searchQueries, isGlobal),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["topics"] });
    },
  });
}

export function useDeleteTopic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (topicId: number) => api.deleteTopic(topicId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["topics"] });
    },
  });
}

export function useRefreshTopic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (topicId: number) => api.refreshTopic(topicId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["topics"] });
    },
  });
}
