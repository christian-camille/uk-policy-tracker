"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
    }: {
      label: string;
      searchQueries: string[];
    }) => api.createTopic(label, searchQueries),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["topics"] });
    },
  });
}

export function useUpdateTopic() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      topicId,
      label,
      searchQueries,
    }: {
      topicId: number;
      label?: string;
      searchQueries?: string[];
    }) => api.updateTopic(topicId, { label, searchQueries }),
    onSuccess: (_data: unknown, variables: { topicId: number; label?: string; searchQueries?: string[] }) => {
      queryClient.invalidateQueries({ queryKey: ["topics"] });
      queryClient.invalidateQueries({ queryKey: ["topic", variables.topicId] });
      queryClient.invalidateQueries({ queryKey: ["actors", variables.topicId] });
      queryClient.invalidateQueries({ queryKey: ["timeline", variables.topicId] });
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
    onSuccess: (_data: unknown, topicId: number) => {
      queryClient.invalidateQueries({ queryKey: ["topics"] });
      queryClient.invalidateQueries({ queryKey: ["timeline", topicId] });
      queryClient.invalidateQueries({ queryKey: ["actors", topicId] });
      queryClient.invalidateQueries({ queryKey: ["topic", topicId] });
    },
  });
}
