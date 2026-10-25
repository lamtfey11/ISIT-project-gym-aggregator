/** Модель предметной области контроллера допуска (adm_access_controller) веб-панели администратора. */

import type { AccessMarkResult, Direction, MarkMethod } from "../../../contracts/ts/contracts.js";

/** Что ввёл администратор на экране «Режим сканирования». */
export interface MarkInput {
  readonly gymId: string;
  readonly direction: Direction;
  /** Строка от ручного сканера QR (HID, режим клавиатуры). */
  readonly passToken?: string;
  /** Клиент, найденный администратором, если QR-пропуск не сгенерировался. */
  readonly userId?: string;
  readonly note?: string;
}

export type MarkStatus = "ALLOWED" | "DENIED" | "QUEUED" | "INVALID" | "RATE_LIMITED" | "FAILED";

/** Итог одной отметки для экрана. */
export interface MarkOutcome {
  readonly status: MarkStatus;
  readonly method: MarkMethod | null;
  readonly direction: Direction;
  readonly idempotencyKey: string | null;
  readonly message: string;
  readonly result: AccessMarkResult | null;
  readonly retryAfterSec: number | null;
}

/** Ошибка сети: запрос мог не дойти до iot_service. */
export class NetworkError extends Error {}

/** Шлюз ответил 429 (контракт RateLimitedError компонента gw_ratelimit). */
export class RateLimitedApiError extends Error {
  constructor(readonly retryAfterSec: number) {
    super(`Слишком частые запросы, повторите через ${retryAfterSec} с`);
  }
}

export class UnknownModeError extends Error {}
