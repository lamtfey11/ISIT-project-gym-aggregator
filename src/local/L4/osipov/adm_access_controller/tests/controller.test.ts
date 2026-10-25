/** Тесты adm_access_controller (node:test). Запуск: npm test. */

import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

import type { AccessMarkResult, AdminAccessMarkRequest } from "../../../contracts/ts/contracts.js";
import {
  AccessController,
  accessReducer,
  initialAccessState,
  ManualMarkStrategy,
  NetworkError,
  normalizeScan,
  OnlineOnlyDelivery,
  QueueExitsOfflineDelivery,
  RateLimitedApiError,
  ScanMarkStrategy,
  UnknownModeError,
} from "../src/index.js";
import type { AccessAction, AccessApi, AccessState, PendingMarksStore } from "../src/index.js";

const GYM = "6f1c2a8e-0000-4000-8000-000000000001";
const TOKEN = "QRPASS-0123456789abcdef";

type Behaviour = "ok" | "deny" | "offline" | "429";

class FakeApi implements AccessApi {
  readonly received: AdminAccessMarkRequest[] = [];
  behaviour: Behaviour = "ok";

  async mark(request: AdminAccessMarkRequest): Promise<AccessMarkResult> {
    if (this.behaviour === "offline") throw new NetworkError("offline");
    if (this.behaviour === "429") throw new RateLimitedApiError(7);
    this.received.push(request);
    return {
      decision: this.behaviour === "ok" ? "ALLOWED" : "DENIED",
      direction: request.direction,
      reason: this.behaviour === "ok" ? null : "Абонемент истёк",
      visit_event_id: this.behaviour === "ok" ? "visit-1" : null,
    };
  }
}

class MemoryPending implements PendingMarksStore {
  private items: AdminAccessMarkRequest[] = [];
  add(request: AdminAccessMarkRequest): void {
    this.items.push(request);
  }
  list(): readonly AdminAccessMarkRequest[] {
    return this.items;
  }
  remove(idempotencyKey: string): void {
    this.items = this.items.filter((r) => r.idempotency_key !== idempotencyKey);
  }
}

describe("AccessController", () => {
  let api: FakeApi;
  let pending: MemoryPending;
  let state: AccessState;
  let controller: AccessController;

  beforeEach(() => {
    api = new FakeApi();
    pending = new MemoryPending();
    state = initialAccessState;
    let n = 0;
    controller = new AccessController(
      [new ScanMarkStrategy(), new ManualMarkStrategy()],
      new QueueExitsOfflineDelivery(),
      api,
      pending,
      { next: (): string => `key-${(n += 1)}` },
      { nowIso: (): string => "2026-10-24T09:00:00Z" },
      (action: AccessAction): void => {
        state = accessReducer(state, action);
      },
    );
  });

  it("скан на входе: запрос по контракту и допуск", async () => {
    const outcome = await controller.submit({ gymId: GYM, direction: "IN", passToken: ` ${TOKEN}\r\n` });
    assert.equal(outcome.status, "ALLOWED");
    assert.deepEqual(api.received[0], {
      gym_id: GYM,
      method: "SCAN",
      direction: "IN",
      pass_token: TOKEN,
      user_id: null,
      note: null,
      idempotency_key: "key-1",
      client_time: "2026-10-24T09:00:00Z",
    });
    assert.equal(state.last?.status, "ALLOWED");
    assert.equal(state.submitting, false);
  });

  it("отказ сервера показывается с причиной", async () => {
    api.behaviour = "deny";
    const outcome = await controller.submit({ gymId: GYM, direction: "IN", passToken: TOKEN });
    assert.equal(outcome.status, "DENIED");
    assert.equal(outcome.message, "Абонемент истёк");
  });

  it("короткая строка со сканера не отправляется", async () => {
    const outcome = await controller.submit({ gymId: GYM, direction: "IN", passToken: "123" });
    assert.equal(outcome.status, "INVALID");
    assert.equal(api.received.length, 0);
  });

  it("ручная отметка, если QR не сгенерировался: нужен клиент и причина", async () => {
    controller.setMode("manual");
    const bad = await controller.submit({ gymId: GYM, direction: "IN", userId: "u-1" });
    assert.equal(bad.status, "INVALID");
    const ok = await controller.submit({ gymId: GYM, direction: "IN", userId: "u-1", note: "QR не открылся" });
    assert.equal(ok.status, "ALLOWED");
    assert.equal(api.received[0]?.method, "MANUAL");
    assert.equal(api.received[0]?.pass_token, null);
    assert.equal(state.mode, "manual");
  });

  it("без связи выход уходит в очередь, вход — нет", async () => {
    api.behaviour = "offline";
    const exit = await controller.submit({ gymId: GYM, direction: "OUT", passToken: TOKEN });
    const entry = await controller.submit({ gymId: GYM, direction: "IN", passToken: TOKEN });
    assert.equal(exit.status, "QUEUED");
    assert.equal(entry.status, "FAILED");
    assert.equal(pending.list().length, 1);
    assert.equal(state.pendingCount, 1);
  });

  it("очередь отправляется повторно с тем же idempotency_key", async () => {
    api.behaviour = "offline";
    const exit = await controller.submit({ gymId: GYM, direction: "OUT", passToken: TOKEN });
    api.behaviour = "ok";
    assert.equal(await controller.flushPending(), 1);
    assert.equal(api.received[0]?.idempotency_key, exit.idempotencyKey);
    assert.equal(state.pendingCount, 0);
  });

  it("подмена политики доставки во время работы", async () => {
    controller.useDeliveryPolicy(new OnlineOnlyDelivery());
    api.behaviour = "offline";
    const exit = await controller.submit({ gymId: GYM, direction: "OUT", passToken: TOKEN });
    assert.equal(exit.status, "FAILED");
    assert.equal(pending.list().length, 0);
    assert.equal(state.deliveryPolicy, "online_only");
  });

  it("ответ 429 шлюза показывает время ожидания", async () => {
    api.behaviour = "429";
    const outcome = await controller.submit({ gymId: GYM, direction: "IN", passToken: TOKEN });
    assert.equal(outcome.status, "RATE_LIMITED");
    assert.equal(outcome.retryAfterSec, 7);
  });

  it("неизвестный режим — ошибка", () => {
    assert.throws(() => controller.setMode("nfc"), UnknownModeError);
  });
});

describe("Вспомогательное", () => {
  it("префикс сканера отрезается", () => {
    assert.equal(normalizeScan("]Q1" + TOKEN + "\n", "]Q1"), TOKEN);
  });

  it("журнал на экране ограничен", () => {
    let s = initialAccessState;
    for (let i = 0; i < 25; i += 1) {
      s = accessReducer(s, {
        type: "access/markFinished",
        outcome: { status: "ALLOWED", method: "SCAN", direction: "IN", idempotencyKey: `k${i}`, message: "", result: null, retryAfterSec: null },
      });
    }
    assert.equal(s.journal.length, 20);
    assert.equal(s.journal[0]?.idempotencyKey, "k24");
  });
});
