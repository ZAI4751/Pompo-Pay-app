/** No GET /payments list exists. Lookup by reference is paymentsService.getByReference. */

import { USE_MOCKS } from "../config";
import type { ApiResult, Paginated } from "@/lib/types/common";
import type { Transaction } from "@/lib/types/transaction";
import { mockTransactions } from "@/mocks/data";

export const transactionsService = {
  async list(): Promise<ApiResult<Paginated<Transaction>>> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      return {
        status: "success",
        data: { items: mockTransactions, total: mockTransactions.length, page: 1, pageSize: 20 },
      };
    }
    return {
      status: "error",
      kind: "unavailable",
      message:
        "There is no transaction list API. Use Payments to retrieve a single payment by reference.",
      httpStatus: 503,
    };
  },
};
