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
      keywordGroups,
      excludedKeywords,
    }: {
      label: string;
      searchQueries?: string[];
      keywordGroups?: string[][];
      excludedKeywords?: string[];
    }) => api.createTopic(label, { searchQueries, keywordGroups, excludedKeywords }),
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
      keywordGroups,
      excludedKeywords,
    }: {
      topicId: number;
      label?: string;
      searchQueries?: string[];
      keywordGroups?: string[][];
      excludedKeywords?: string[];
    }) => api.updateTopic(topicId, { label, searchQueries, keywordGroups, excludedKeywords }),
    onSuccess: (_data: unknown, variables: { topicId: number; label?: string; searchQueries?: string[]; keywordGroups?: string[][]; excludedKeywords?: string[] }) => {
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

export function useRefreshAllTopics() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.refreshAllTopics(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["topics"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["actors"] });
      queryClient.invalidateQueries({ queryKey: ["topic"] });
    },
  });
}
