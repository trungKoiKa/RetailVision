import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../shared/api/client";
import type { Overview } from "../../shared/types/api";

export const OVERVIEW_POLL_MS = 2000;

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: () => apiFetch<Overview>("/api/overview"),
    refetchInterval: OVERVIEW_POLL_MS,
    retry: false,
  });
}
