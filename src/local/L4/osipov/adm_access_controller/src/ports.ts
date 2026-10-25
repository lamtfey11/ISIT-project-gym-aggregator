/** Порты контроллера: соседние компоненты admin_web по диаграмме L3. */

import type { AccessMarkResult, AdminAccessMarkRequest } from "../../../contracts/ts/contracts.js";

/** Реализует adm_api_client: POST /api/v1/access/marks через api_gateway в iot_service. */
export interface AccessApi {
  /** Бросает NetworkError при обрыве связи и RateLimitedApiError при ответе 429. */
  mark(request: AdminAccessMarkRequest): Promise<AccessMarkResult>;
}

/** Реализует adm_state_store (sessionStorage): отметки, ожидающие повторной отправки. */
export interface PendingMarksStore {
  add(request: AdminAccessMarkRequest): void;
  list(): readonly AdminAccessMarkRequest[];
  remove(idempotencyKey: string): void;
}

export interface IdGenerator {
  next(): string;
}

export interface Clock {
  nowIso(): string;
}
