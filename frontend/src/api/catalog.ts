import { api } from "./client";
import type {
  Category,
  CategoryTreeNode,
  CsvImportResult,
  Page,
  Part,
  PriceHistoryEntry,
} from "@/types";

// --- категории ---

export async function listCategories(): Promise<Category[]> {
  const { data } = await api.get<Category[]>("/categories");
  return data;
}

export async function getCategoryTree(): Promise<CategoryTreeNode[]> {
  const { data } = await api.get<CategoryTreeNode[]>("/categories/tree");
  return data;
}

export interface CategoryInput {
  name: string;
  slug: string;
  parent_id?: string | null;
}

export async function createCategory(payload: CategoryInput): Promise<Category> {
  const { data } = await api.post<Category>("/categories", payload);
  return data;
}

export async function updateCategory(
  id: string,
  payload: Partial<CategoryInput>,
): Promise<Category> {
  const { data } = await api.patch<Category>(`/categories/${id}`, payload);
  return data;
}

export async function deleteCategory(id: string): Promise<void> {
  await api.delete(`/categories/${id}`);
}

// --- запчасти ---

export interface PartListParams {
  category_id?: string;
  search?: string;
  price_min?: number | string;
  price_max?: number | string;
  in_stock?: boolean;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}

export async function listParts(params: PartListParams = {}): Promise<Page<Part>> {
  const { data } = await api.get<Page<Part>>("/parts", { params });
  return data;
}

export async function getPart(id: string): Promise<Part> {
  const { data } = await api.get<Part>(`/parts/${id}`);
  return data;
}

export async function getPriceHistory(id: string): Promise<PriceHistoryEntry[]> {
  const { data } = await api.get<PriceHistoryEntry[]>(`/parts/${id}/price-history`);
  return data;
}

export interface PartInput {
  article: string;
  name: string;
  description?: string | null;
  manufacturer?: string | null;
  category_id?: string | null;
  price: string | number;
  stock_quantity?: number;
  unit?: string;
}

export async function createPart(payload: PartInput): Promise<Part> {
  const { data } = await api.post<Part>("/parts", payload);
  return data;
}

export async function updatePart(
  id: string,
  payload: Partial<PartInput>,
): Promise<Part> {
  const { data } = await api.patch<Part>(`/parts/${id}`, payload);
  return data;
}

export async function activatePart(id: string): Promise<void> {
  await api.post(`/parts/${id}/activate`);
}

export async function deactivatePart(id: string): Promise<void> {
  await api.post(`/parts/${id}/deactivate`);
}

export async function importCsv(file: File): Promise<CsvImportResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<CsvImportResult>("/parts/import/csv", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
