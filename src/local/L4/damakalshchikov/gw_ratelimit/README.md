# gw_ratelimit — модуль ограничения нагрузки API-шлюза (ЛР3, C4 L4)

Контейнер: `api_gateway` (Nginx). Компонент: `gw_ratelimit` (на L3 — `ratelimit_comp`). Автор: Дамакальщиков М.

Код написан на TypeScript и исполняется внутри Nginx модулем **njs** (nginx JavaScript, движок QuickJS).
Штатный `limit_req` умеет только одно правило «утечки ведра» на зону и ключ по переменной — его нельзя
подменить алгоритмом во время работы, поэтому для ЛР3 частота запросов ограничивается njs-модулем,
а `limit_conn` (число соединений с IP) остаётся штатным.

## Шаблон «Стратегия» (два семейства)

| Роль | Как считать | Кого считать |
|---|---|---|
| Контекст | `RateLimiter` | `RateLimiter` |
| Интерфейс | `RateLimitAlgorithm.check(key, spec, nowMs, store)` | `ClientKeyStrategy.keyFor(request)` |
| Стратегии | `FixedWindowAlgorithm`, `SlidingWindowAlgorithm`, `TokenBucketAlgorithm` | `IpKeyStrategy`, `BearerTokenKeyStrategy` |
| Подмена | `useAlgorithm(policyName, algorithm)` | `useKeyStrategy(policyName, keyStrategy)` |

Политики маршрутов (`buildDefaultPolicies`, первая подходящая выигрывает):

| Политика | Маршрут | Алгоритм | Лимит | Ключ | Дальше |
|---|---|---|---|---|---|
| `auth_login` | `POST /api/v1/auth/login` | fixed_window | 10 / 60 с | ip | `@user_api` |
| `access_marks` | `/api/v1/access/` (сканер и ручные отметки) | token_bucket | 60 / 60 с, всплеск 30 | bearer_token | `@user_api` |
| `payment_webhooks` | `POST /webhooks/` | sliding_window | 600 / 60 с | ip | `@partner` |
| `bi_read` | `/bi/` | sliding_window | 120 / 60 с | ip | `@partner` |
| `user_api` | `/api/` | sliding_window | 120 / 60 с | bearer_token | `@user_api` |

* Ответ при превышении — 429 с телом по общему контракту `RateLimitedError` (`{"error":"rate_limited","retry_after":N}`)
  и заголовком `Retry-After`; на всех ответах — `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Policy`.
* Ключ `bearer_token` — хэш строки токена, а не его содержимое: JWT проверяется позже (`gw_authcheck`).
  Клиенты за одним NAT (Wi-Fi зала) не делят лимит; без токена — откат на IP.
* Счётчики лежат в общей для worker-процессов зоне `js_shared_dict_zone` (`NjsSharedDictStore`).
  `incr` атомарен; корзина `token_bucket` читается и пишется двумя операциями — возможна погрешность
  в несколько запросов при одновременных обращениях из разных worker, это допустимо.

## Изменение на L3

Строку технологии `gw_ratelimit` поменять с «Nginx / limit_req, limit_conn» на
**«Nginx / njs (TypeScript), limit_conn»**.

## Сборка и проверка

```bash
npm install                 # typescript, esbuild, @types/node
npm run typecheck           # tsc в строгом режиме (strict, exactOptionalPropertyTypes, noUncheckedIndexedAccess)
npm test                    # 14 тестов node:test
npm run build               # dist/gw_ratelimit.js — один ES-модуль для js_import
```

Подключение в шлюзе — `nginx/gw_ratelimit.conf` (нужен njs ≥ 0.8.8, `js_engine qjs`).

## Файлы

* `diagram/L4_gw_ratelimit.puml` — UML-диаграмма классов (C4 L4)
* `src/` — код; `src/types/njs.d.ts` — нужное подмножество типов njs
* `tests/limiter.test.ts` — тесты, в том числе подмена алгоритма и ключа во время работы (OCP)
* `dist/gw_ratelimit.js` — собранный модуль для Nginx
