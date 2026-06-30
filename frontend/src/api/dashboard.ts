import { api } from "./client";
import type { DashboardSummary, PeriodPreset } from "@/types";

export interface DashboardParams {
  period?: PeriodPreset;
  date_from?: string; // YYYY-MM-DD
  date_to?: string; // YYYY-MM-DD
}

export async function getDashboardSummary(
  params?: DashboardParams,
): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>("/dashboard/summary", {
    params,
  });
  return data;
}
