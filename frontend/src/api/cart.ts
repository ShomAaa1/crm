import { api } from "./client";
import type { CartSummary } from "@/types";

export async function getCart(): Promise<CartSummary> {
  const { data } = await api.get<CartSummary>("/cart");
  return data;
}

export async function addToCart(
  part_id: string,
  quantity: number,
): Promise<CartSummary> {
  const { data } = await api.post<CartSummary>("/cart/items", {
    part_id,
    quantity,
  });
  return data;
}

export async function setQuantity(
  part_id: string,
  quantity: number,
): Promise<CartSummary> {
  const { data } = await api.patch<CartSummary>(`/cart/items/${part_id}`, {
    quantity,
  });
  return data;
}

export async function removeItem(part_id: string): Promise<CartSummary> {
  const { data } = await api.delete<CartSummary>(`/cart/items/${part_id}`);
  return data;
}

export async function clearCart(): Promise<void> {
  await api.delete("/cart");
}
