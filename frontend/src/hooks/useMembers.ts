"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useTrackedMembers() {
  return useQuery({
    queryKey: ["members"],
    queryFn: () => api.getTrackedMembers(),
  });
}

export function useMemberSearch(name: string) {
  return useQuery({
    queryKey: ["memberSearch", name],
    queryFn: () => api.searchMembers(name),
    enabled: name.length >= 2,
  });
}

export function useMember(parliamentId: number) {
  return useQuery({
    queryKey: ["member", parliamentId],
    queryFn: () => api.getMember(parliamentId),
    enabled: parliamentId > 0,
  });
}

export function useMemberVotes(parliamentId: number, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["memberVotes", parliamentId, params],
    queryFn: () => api.getMemberVotes(parliamentId, params),
    enabled: parliamentId > 0,
  });
}

export function useMemberQuestions(parliamentId: number, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["memberQuestions", parliamentId, params],
    queryFn: () => api.getMemberQuestions(parliamentId, params),
    enabled: parliamentId > 0,
  });
}

export function useTrackMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (parliamentId: number) => api.trackMember(parliamentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members"] });
      queryClient.invalidateQueries({ queryKey: ["memberSearch"] });
    },
  });
}

export function useUntrackMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (parliamentId: number) => api.untrackMember(parliamentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members"] });
    },
  });
}

export function useRefreshMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (parliamentId: number) => api.refreshMember(parliamentId),
    onSuccess: (_data: unknown, parliamentId: number) => {
      queryClient.invalidateQueries({ queryKey: ["members"] });
      queryClient.invalidateQueries({ queryKey: ["member", parliamentId] });
      queryClient.invalidateQueries({ queryKey: ["memberVotes", parliamentId] });
      queryClient.invalidateQueries({ queryKey: ["memberQuestions", parliamentId] });
    },
  });
}

export function useRefreshAllMembers() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.refreshAllMembers(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members"] });
      queryClient.invalidateQueries({ queryKey: ["member"] });
      queryClient.invalidateQueries({ queryKey: ["memberVotes"] });
      queryClient.invalidateQueries({ queryKey: ["memberQuestions"] });
    },
  });
}
