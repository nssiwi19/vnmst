import type { VietQrResponse } from "../types";

const PATH = "/vietqr-api/v2/business";

function normalizeMst(input: string): string {
  return input.replace(/\D/g, "").trim();
}

export async function fetchBusinessByTaxCode(mstRaw: string): Promise<VietQrResponse> {
  const taxCode = normalizeMst(mstRaw);
  if (!taxCode) {
    return { code: "98", desc: "MST rỗng", data: null };
  }

  const url = `${PATH}/${encodeURIComponent(taxCode)}`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  const body = (await res.json()) as VietQrResponse;

  if (!res.ok) {
    return {
      code: String(res.status),
      desc: body?.desc ?? res.statusText,
      data: null,
    };
  }
  return body;
}

export { normalizeMst };
