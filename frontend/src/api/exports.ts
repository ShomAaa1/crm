import { api } from "./client";

async function downloadXlsx(path: string, filename: string): Promise<void> {
  const response = await api.get(path, { responseType: "blob" });
  const blob = new Blob([response.data], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

function stamp(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10).replace(/-/g, "");
}

export async function exportRequests(): Promise<void> {
  await downloadXlsx("/exports/requests.xlsx", `requests_${stamp()}.xlsx`);
}

export async function exportProposals(): Promise<void> {
  await downloadXlsx("/exports/proposals.xlsx", `proposals_${stamp()}.xlsx`);
}

export async function exportOrders(): Promise<void> {
  await downloadXlsx("/exports/orders.xlsx", `orders_${stamp()}.xlsx`);
}
