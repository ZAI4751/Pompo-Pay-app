/** MOCK service -- transactions are a future backend milestone entirely. */

import type { ApiResult, Paginated } from "@/lib/types/common";
import type { Transaction } from "@/lib/types/transaction";
import { mockTransactions } from "@/mocks/data";

const LATENCY_MS = 300;

export const transactionsService = {
  async list(): Promise<ApiResult<Paginated<Transaction>>> {
    await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
    return {
      status: "success",
      data: { items: mockTransactions, total: mockTransactions.length, page: 1, pageSize: 20 },
    };
  },
};
