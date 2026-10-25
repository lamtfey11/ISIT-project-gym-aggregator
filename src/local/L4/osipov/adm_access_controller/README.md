# adm_access_controller — контроллер допуска веб-панели (ЛР3, C4 L4)

Контейнер: `admin_web` (React 18 / TypeScript, Vite). Компонент: `adm_access_controller`. Автор: Осипов И.

Логика экрана «Режим сканирования» у стойки администратора: принимает строку QR-пропуска с ручного
сканера (USB/Bluetooth, работает как клавиатура) и направление «вход / выход», собирает запрос по контракту
`AdminAccessMarkRequest`, отправляет его через клиент API-шлюза в `iot_service` и показывает результат.
Если у клиента не сгенерировался QR, администратор делает ручную отметку с обязательной причиной.
Входы и выходы учитываются всегда.

## Шаблон «Стратегия» (два семейства)

| Роль | Как отметить | Что делать без связи |
|---|---|---|
| Контекст | `AccessController` | `AccessController` |
| Интерфейс | `MarkModeStrategy.validate / buildRequest` | `DeliveryPolicy.deliver(request, api, pending)` |
| Стратегии | `ScanMarkStrategy`, `ManualMarkStrategy` | `OnlineOnlyDelivery`, `QueueExitsOfflineDelivery` |
| Подмена | `setMode("scan" \| "manual")` | `useDeliveryPolicy(policy)` |

* `queue_exits_offline` (по умолчанию): при обрыве Wi-Fi **выход** сохраняется в `adm_state_store` и
  отправляется позже (`flushPending`) с тем же `idempotency_key` — `iot_service` не удвоит посещение.
  **Вход** без проверки пропуска не допускается: это был бы проход без абонемента.
* Ответ шлюза 429 (`RateLimitedError` от `gw_ratelimit`) показывается как «повторите через N с».

Состояние экрана — Redux: действия `AccessAction` и чистый редьюсер `accessReducer`
(подключается в `adm_state_store`: `configureStore({ reducer: { access: accessReducer } })`).
Сам контроллер не зависит от React и Redux Toolkit — получает `dispatch` через конструктор, поэтому
тестируется без браузера.

## Сборка и проверка

```bash
npm install
npm run typecheck   # tsc strict, exactOptionalPropertyTypes, noUncheckedIndexedAccess
npm test            # 11 тестов node:test
```

## Файлы

* `diagram/L4_adm_access_controller.puml` — UML-диаграмма классов (C4 L4)
* `src/` — код: `modes.ts`, `delivery.ts`, `controller.ts`, `accessSlice.ts`, `ports.ts`, `domain.ts`
* `tests/controller.test.ts` — тесты, в том числе подмена режима и политики доставки во время работы
