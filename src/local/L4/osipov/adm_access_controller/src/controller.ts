/** Контекст шаблона «Стратегия»: контроллер допуска (adm_access_controller). */

import type { AdminAccessMarkRequest, Direction } from "../../../contracts/ts/contracts.js";
import type { Dispatch } from "./accessSlice.js";
import type { DeliveryPolicy } from "./delivery.js";
import { NetworkError, RateLimitedApiError, UnknownModeError } from "./domain.js";
import type { MarkInput, MarkOutcome } from "./domain.js";
import type { MarkModeStrategy } from "./modes.js";
import type { AccessApi, Clock, IdGenerator, PendingMarksStore } from "./ports.js";

export class AccessController {
  private readonly modes = new Map<string, MarkModeStrategy>();
  private mode: MarkModeStrategy;

  constructor(
    modes: readonly MarkModeStrategy[],
    private delivery: DeliveryPolicy,
    private readonly api: AccessApi,
    private readonly pending: PendingMarksStore,
    private readonly ids: IdGenerator,
    private readonly clock: Clock,
    private readonly dispatch: Dispatch,
  ) {
    const [first] = modes;
    if (first === undefined) {
      throw new UnknownModeError("Нужен хотя бы один режим отметки");
    }
    for (const m of modes) {
      this.modes.set(m.name, m);
    }
    this.mode = first;
  }

  /** Переключение режима: «Сканирование» ↔ «Ручная отметка» (QR не сгенерировался). */
  setMode(name: string): void {
    const found = this.modes.get(name);
    if (found === undefined) {
      throw new UnknownModeError(`Нет режима ${name}`);
    }
    this.mode = found;
    this.dispatch({ type: "access/modeChanged", mode: name });
  }

  setDirection(direction: Direction): void {
    this.dispatch({ type: "access/directionChanged", direction });
  }

  /** Подмена политики доставки во время работы (например, отключить очередь на время сверки). */
  useDeliveryPolicy(policy: DeliveryPolicy): void {
    this.delivery = policy;
    this.dispatch({ type: "access/deliveryPolicyChanged", policy: policy.name });
  }

  async submit(input: MarkInput): Promise<MarkOutcome> {
    const errors = this.mode.validate(input);
    if (errors.length > 0) {
      return this.finish(this.outcome("INVALID", input.direction, null, errors.join("; ")));
    }
    const request = this.mode.buildRequest(input, { idempotencyKey: this.ids.next(), clientTime: this.clock.nowIso() });
    this.dispatch({ type: "access/markSubmitted" });
    try {
      const delivered = await this.delivery.deliver(request, this.api, this.pending);
      this.dispatch({ type: "access/pendingChanged", count: this.pending.list().length });
      if (delivered.kind === "queued") {
        return this.finish(this.outcome("QUEUED", input.direction, request, "Нет связи: выход сохранён и будет отправлен"));
      }
      const { result } = delivered;
      return this.finish({
        ...this.outcome(result.decision, result.direction, request, result.reason ?? "Проход отмечен"),
        result,
      });
    } catch (error) {
      if (error instanceof RateLimitedApiError) {
        return this.finish({ ...this.outcome("RATE_LIMITED", input.direction, request, error.message), retryAfterSec: error.retryAfterSec });
      }
      const message = error instanceof NetworkError ? "Нет связи с сервером: повторите отметку" : "Ошибка отметки";
      return this.finish(this.outcome("FAILED", input.direction, request, message));
    }
  }

  /** Повторная отправка накопленных выходов, когда связь вернулась. Возвращает число отправленных. */
  async flushPending(): Promise<number> {
    let sent = 0;
    for (const request of [...this.pending.list()]) {
      try {
        await this.api.mark(request);
        this.pending.remove(request.idempotency_key);
        sent += 1;
      } catch (error) {
        if (error instanceof NetworkError || error instanceof RateLimitedApiError) {
          break;
        }
        this.pending.remove(request.idempotency_key); // сервер отклонил — повтор не поможет
      }
    }
    this.dispatch({ type: "access/pendingChanged", count: this.pending.list().length });
    return sent;
  }

  private outcome(
    status: MarkOutcome["status"],
    direction: Direction,
    request: AdminAccessMarkRequest | null,
    message: string,
  ): MarkOutcome {
    return {
      status,
      method: request?.method ?? this.mode.method,
      direction,
      idempotencyKey: request?.idempotency_key ?? null,
      message,
      result: null,
      retryAfterSec: null,
    };
  }

  private finish(outcome: MarkOutcome): MarkOutcome {
    this.dispatch({ type: "access/markFinished", outcome });
    return outcome;
  }
}
