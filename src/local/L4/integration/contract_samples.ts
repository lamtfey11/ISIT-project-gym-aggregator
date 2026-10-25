/**
 * Образцы сообщений, которые TypeScript-компоненты реально отправляют на стыках.
 * check_contracts.py собирает этот файл, запускает его и валидирует вывод Python-моделями fitagg_contracts:
 * так проверяется, что admin_web и api_gateway говорят с Python-сервисами на одном контракте.
 */

import { randomUUID } from "node:crypto";

import { RateLimiter, rateLimitedBody } from "../damakalshchikov/gw_ratelimit/src/limiter.js";
import { buildDefaultPolicies } from "../damakalshchikov/gw_ratelimit/src/policies.js";
import { InMemoryCounterStore, ManualClock } from "../damakalshchikov/gw_ratelimit/src/store.js";
import { ManualMarkStrategy, ScanMarkStrategy } from "../osipov/adm_access_controller/src/modes.js";

const meta = () => ({ idempotencyKey: randomUUID(), clientTime: new Date(Date.UTC(2026, 9, 24, 9)).toISOString() });
const gymId = randomUUID();

const scan = new ScanMarkStrategy().buildRequest({ gymId, direction: "IN", passToken: "QRPASS-0123456789abcdef\r\n" }, meta());
const manual = new ManualMarkStrategy().buildRequest(
  { gymId, direction: "OUT", userId: randomUUID(), note: "QR не сгенерировался" },
  meta(),
);

const clock = new ManualClock(Date.UTC(2026, 9, 24, 9));
const limiter = new RateLimiter(buildDefaultPolicies(), new InMemoryCounterStore(clock), clock);
let denied = null;
for (let i = 0; i < 20 && denied === null; i += 1) {
  const d = limiter.check({ method: "POST", path: "/api/v1/auth/login", clientIp: "10.0.0.1", authorization: null });
  if (d !== null && !d.allowed) denied = d;
}
if (denied === null) throw new Error("лимит входа не сработал");

process.stdout.write(
  JSON.stringify({
    AdminAccessMarkRequest: [scan, manual],
    RateLimitedError: [rateLimitedBody(denied)],
  }),
);
