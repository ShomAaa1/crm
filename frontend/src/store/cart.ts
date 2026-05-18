import { create } from "zustand";
import * as cartApi from "@/api/cart";
import type { CartSummary } from "@/types";

interface CartState {
  summary: CartSummary | null;
  loading: boolean;
  refresh: () => Promise<void>;
  add: (part_id: string, quantity: number) => Promise<void>;
  setQty: (part_id: string, quantity: number) => Promise<void>;
  remove: (part_id: string) => Promise<void>;
  clear: () => Promise<void>;
  reset: () => void;
}

export const useCartStore = create<CartState>((set) => ({
  summary: null,
  loading: false,

  async refresh() {
    set({ loading: true });
    try {
      const data = await cartApi.getCart();
      set({ summary: data });
    } catch {
      // если не клиент — просто оставляем null
      set({ summary: null });
    } finally {
      set({ loading: false });
    }
  },

  async add(part_id, quantity) {
    const data = await cartApi.addToCart(part_id, quantity);
    set({ summary: data });
  },

  async setQty(part_id, quantity) {
    const data = await cartApi.setQuantity(part_id, quantity);
    set({ summary: data });
  },

  async remove(part_id) {
    const data = await cartApi.removeItem(part_id);
    set({ summary: data });
  },

  async clear() {
    await cartApi.clearCart();
    set({ summary: { items: [], items_count: 0, total: "0.00" } });
  },

  reset() {
    set({ summary: null });
  },
}));
