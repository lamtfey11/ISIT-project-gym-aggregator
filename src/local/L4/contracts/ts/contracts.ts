export type Direction = "IN" | "OUT";
export type MarkMethod = "SCAN" | "MANUAL";

/** admin_web -> api_gateway -> iot_service (TCP 8004). */
export interface AdminAccessMarkRequest {
  readonly gym_id: string;
  readonly method: MarkMethod;
  readonly direction: Direction;
  readonly pass_token: string | null;
  readonly user_id: string | null;
  readonly note: string | null;
  readonly idempotency_key: string;
  readonly client_time: string;
}

/** Ответ iot_service на отметку администратора. */
export interface AccessMarkResult {
  readonly decision: "ALLOWED" | "DENIED";
  readonly direction: Direction;
  readonly reason: string | null;
  readonly visit_event_id: string | null;
}

/** Тело ответа API-шлюза 429; то же число секунд в заголовке Retry-After. */
export interface RateLimitedError {
  readonly error: "rate_limited";
  readonly retry_after: number;
}
