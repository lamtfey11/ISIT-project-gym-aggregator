/** Режимы отметки (семейство стратегий № 1): как из ввода администратора собрать запрос к iot_service. */

import type { AdminAccessMarkRequest, MarkMethod } from "../../../contracts/ts/contracts.js";
import type { MarkInput } from "./domain.js";

export interface RequestMeta {
  readonly idempotencyKey: string;
  readonly clientTime: string;
}

export interface MarkModeStrategy {
  readonly name: string;
  readonly method: MarkMethod;
  /** Пустой список — ввод корректен; иначе тексты ошибок для формы. */
  validate(input: MarkInput): string[];
  buildRequest(input: MarkInput, meta: RequestMeta): AdminAccessMarkRequest;
}

/** Ручной сканер работает как клавиатура: к строке могут прилипнуть пробелы, CR/LF и префикс сканера. */
export function normalizeScan(raw: string, prefix: string = ""): string {
  const trimmed = raw.replace(/[\r\n\t]/g, "").trim();
  return prefix !== "" && trimmed.startsWith(prefix) ? trimmed.slice(prefix.length) : trimmed;
}

/** Основной режим: отметка по QR-пропуску со сканера на входе или выходе. */
export class ScanMarkStrategy implements MarkModeStrategy {
  readonly name = "scan";
  readonly method: MarkMethod = "SCAN";

  /** prefix — служебный префикс, если сканер настроен его добавлять. */
  constructor(private readonly scannerPrefix: string = "") {}

  validate(input: MarkInput): string[] {
    const token = normalizeScan(input.passToken ?? "", this.scannerPrefix);
    const errors: string[] = [];
    if (token.length < 16 || token.length > 512) {
      errors.push("Строка пропуска не похожа на QR-пропуск: отсканируйте ещё раз");
    }
    if (input.userId !== undefined) {
      errors.push("В режиме сканирования клиента не выбирают вручную");
    }
    return errors;
  }

  buildRequest(input: MarkInput, meta: RequestMeta): AdminAccessMarkRequest {
    return {
      gym_id: input.gymId,
      method: this.method,
      direction: input.direction,
      pass_token: normalizeScan(input.passToken ?? "", this.scannerPrefix),
      user_id: null,
      note: input.note ?? null,
      idempotency_key: meta.idempotencyKey,
      client_time: meta.clientTime,
    };
  }
}

/** Запасной режим: ручная отметка, если у клиента не сгенерировался QR-пропуск. Причина обязательна. */
export class ManualMarkStrategy implements MarkModeStrategy {
  readonly name = "manual";
  readonly method: MarkMethod = "MANUAL";

  validate(input: MarkInput): string[] {
    const errors: string[] = [];
    if (input.userId === undefined || input.userId === "") {
      errors.push("Выберите клиента");
    }
    if (input.passToken !== undefined) {
      errors.push("При ручной отметке строку пропуска не передают");
    }
    const note = (input.note ?? "").trim();
    if (note.length < 3 || note.length > 200) {
      errors.push("Укажите причину ручной отметки (3–200 символов)");
    }
    return errors;
  }

  buildRequest(input: MarkInput, meta: RequestMeta): AdminAccessMarkRequest {
    return {
      gym_id: input.gymId,
      method: this.method,
      direction: input.direction,
      pass_token: null,
      user_id: input.userId ?? null,
      note: (input.note ?? "").trim(),
      idempotency_key: meta.idempotencyKey,
      client_time: meta.clientTime,
    };
  }
}
