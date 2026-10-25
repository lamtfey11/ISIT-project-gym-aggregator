/** Политики доставки отметки (семейство стратегий № 2): что делать, если связь с сервером пропала. */

import type { AccessMarkResult, AdminAccessMarkRequest } from "../../../contracts/ts/contracts.js";
import { NetworkError } from "./domain.js";
import type { AccessApi, PendingMarksStore } from "./ports.js";

export type DeliveryResult =
  | { readonly kind: "delivered"; readonly result: AccessMarkResult }
  | { readonly kind: "queued" };

export interface DeliveryPolicy {
  readonly name: string;
  deliver(request: AdminAccessMarkRequest, api: AccessApi, pending: PendingMarksStore): Promise<DeliveryResult>;
}

/** Только онлайн: при обрыве связи ошибка показывается администратору, отметку повторяют вручную. */
export class OnlineOnlyDelivery implements DeliveryPolicy {
  readonly name = "online_only";

  async deliver(request: AdminAccessMarkRequest, api: AccessApi): Promise<DeliveryResult> {
    return { kind: "delivered", result: await api.mark(request) };
  }
}

/**
 * Выходы — в очередь при обрыве связи, входы — только онлайн.
 * Вход без проверки пропуска означает допуск без абонемента, а выход ничего не разрешает:
 * его безопасно отправить позже. Повтор не удвоит посещение — iot_service распознаёт
 * повтор по idempotency_key.
 */
export class QueueExitsOfflineDelivery implements DeliveryPolicy {
  readonly name = "queue_exits_offline";

  async deliver(request: AdminAccessMarkRequest, api: AccessApi, pending: PendingMarksStore): Promise<DeliveryResult> {
    try {
      return { kind: "delivered", result: await api.mark(request) };
    } catch (error) {
      if (error instanceof NetworkError && request.direction === "OUT") {
        pending.add(request);
        return { kind: "queued" };
      }
      throw error;
    }
  }
}
