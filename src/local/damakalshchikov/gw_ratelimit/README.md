# gw_ratelimit: модуль ограничения нагрузки API-шлюза (ЛР3, C4 L4)

Контейнер: `api_gateway` (Nginx). Компонент L3: `ratelimit_comp`.
Код написан на TypeScript и исполняется внутри Nginx модулем **njs** (nginx JavaScript, движок QuickJS).


## Шаблон "Стратегия"

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

* Ответ при превышении - 429 с телом по общему контракту `RateLimitedError` (`{"error":"rate_limited","retry_after":N}`)
  и заголовком `Retry-After`; на всех ответах - `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Policy`
* Ключ `bearer_token` - хэш строки токена, а не его содержимое: JWT проверяется позже (`authcheck_comp`).
  Клиенты за одним NAT (Wi-Fi зала) не делят лимит
* Счётчики лежат в общей для worker-процессов зоне `js_shared_dict_zone` (`NjsSharedDictStore`).
  `incr` атомарен; корзина `token_bucket` читается и пишется двумя операциями

## Изменение на L3

Строку технологии `ratelimit_comp` поменять с «Nginx / limit_req, limit_conn» на
**«Nginx / njs (TypeScript), limit_conn»**.

## Сборка и проверка

```bash
npm install                 # typescript, esbuild, @types/node
npm run typecheck           # tsc в строгом режиме (strict, exactOptionalPropertyTypes, noUncheckedIndexedAccess)
npm run build               # dist/gw_ratelimit.js — один ES-модуль для js_import
```

## Файлы

* `src/`: код;
* `src/types/njs.d.ts`: нужное подмножество типов njs
* `dist/gw_ratelimit.js`: собранный модуль для Nginx
