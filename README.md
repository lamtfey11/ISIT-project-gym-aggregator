# ИС-агрегатор фитнес-клубов

Информационная система-агрегатор для малых независимых фитнес-залов и студий. Клиент находит зал рядом, покупает абонемент онлайн и проходит в зал по электронному QR-пропуску. Зал получает готовый канал продаж, аналитику посещений и выплаты, платформа зарабатывает на комиссии с платежей (маркетплейс-схема).

Курсовой проект по дисциплине «Информационные системы и технологии».

## Идея

На рынке много малых залов, у которых нет ресурсов на своё приложение, маркетинг и онлайн-оплату. Существующие агрегаторы (1Fit, GOGYM и другие) продают единую подписку на пул уже раскрученных клубов и не продвигают отдельные малые залы. Мы закрываем именно эту нишу: витрина и онлайн-касса для конкретных малых залов.

Ключевые возможности:

- геопоиск залов рядом с фильтрами по цене, типу тренировок и рейтингу;
- онлайн-оплата абонемента внутри приложения, сплит-платежи между залом и платформой;
- электронный QR-пропуск и допуск через СКУД зала (MQTT);
- индекс загруженности зала по 10-балльной шкале;
- кабинет партнёра: карточка зала, тарифы, расписание, отчёты;
- аналитика и отчётность для залов и платформы, выгрузки для бухгалтерии.

## Команда

| Участник | Роль | Зона ответственности |
|---|---|---|
| Лисов Матфей | Тимлид | Общая архитектура, сводные диаграммы, глоссарий ID, СУБД, общие контракты `contracts`, ревью Pull Request'ов; сервис интеграций и уведомлений, сервис допуска и загруженности (контур СКУД, MQTT) |
| Осипов Илья | Frontend | Мобильное приложение, веб-панель (в том числе режим сканирования QR-пропусков у стойки), вход через провайдера идентификации, QR-пропуск |
| Кутенков Сергей | Backend | Сервис авторизации, сервис бизнес-логики (каталог, тарифы, абонементы, расчёт цены и комиссии) |
| Эрендженова Мария | Аналитик | Сервис отчётности, ETL, ClickHouse, интеграции с BI-платформой и 1С |
| Дамакальщиков Михаил | DevOps | API-шлюз, брокеры, кэш, объектное хранилище, наблюдаемость, CI/CD |

## Архитектура (C4)

Архитектура описана в PlantUML по модели C4.

**Уровень 1, контекст.** Система как чёрный ящик, пять ролей и семь внешних систем: платёжный шлюз, картографический сервис, сервисы доставки уведомлений, СКУД и датчики залов, провайдер идентификации (VK ID, Sber ID), BI-платформа (Yandex DataLens), система бухгалтерского учёта (1С). На диаграмме 18 связей.

**Уровень 2, контейнеры.** Шестнадцать контейнеров, закреплённых за зонами участников, и 57 связей. Архитектура сервисная: сервисы независимо разворачиваются и общаются через API и брокеры, но пять из них используют одну общую PostgreSQL. У каждой таблицы один сервис-владелец, остальные узнают об изменениях из доменных событий.

Наружу открыты только порты 443 (API-шлюз) и 8883 (MQTT-брокер для СКУД), остальное во внутренней сети.

**Уровень 3, компоненты.** Для десяти контейнеров, в которых команда пишет или настраивает собственную логику, построены диаграммы компонентов: `mobile_app`, `admin_web`, `api_gateway`, `auth_service`, `core_api`, `integration_service`, `iot_service`, `analytics_service`, `etl_service`, `monitoring`. Всего на них 90 компонентов. Для шести контейнеров (`database`, `cache`, `object_storage`, `dwh`, `message_broker`, `mqtt_broker`) диаграммы компонентов не строятся: это готовые хранилища и брокеры, и в диаграммах уровня 3 они показаны чёрными ящиками. Диаграммы уровня 3 остаются локальными, в одну сводную схему они не собираются: 90 компонентов на одном рисунке нечитаемы. Стыковка уровней 2 и 3 ведётся таблицами в разделе «Глобальный глоссарий компонентов».

**Уровень 4, код.** Каждый участник детализировал до кода один компонент своего контейнера: UML-диаграмма классов и код на языке контейнера с шаблоном «Стратегия», строгой типизацией и принципами SOLID. Типы данных на стыках контейнеров общие для всех и лежат в пакете `contracts`. Подробности в разделе «Уровень 4: диаграммы кода».

### Технологический стек

| Узел | Технология |
|---|---|
| Серверная часть | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Доменные события | RabbitMQ 3, AMQP 0-9-1 (aio-pika, pika), topic-обменник, JSON-конверт с `event_id` |
| Фоновые задачи | Celery, только внутри `integration_service` (выплаты, повторы отправки) |
| Мобильное приложение | React Native, TypeScript |
| Веб-панель | React 18, TypeScript, Vite, Redux Toolkit |
| Ручной сканер администратора | USB- или Bluetooth-сканер QR-кодов в режиме клавиатуры (HID), работает с веб-панелью без драйверов |
| API-шлюз | Nginx, njs (TypeScript) для ограничения частоты запросов |
| База данных | PostgreSQL 16 + PostGIS 3 |
| Кэш и сессии | Redis 7 |
| Брокер СКУД | Eclipse Mosquitto 2.0 (MQTT) |
| Аналитика | ClickHouse, Apache Airflow, pandas |
| Объектное хранилище | MinIO (S3 API) |
| Наблюдаемость | Prometheus, Alertmanager, Grafana, Loki |
| Доставка | Docker / Docker Compose, GitHub Actions, GHCR |

## Глобальный глоссарий ID

Все сводные диаграммы используют только эти идентификаторы. Локальные представления участников остаются самодостаточными для личной защиты, соответствие их ID глобальным приведено ниже.

### Проектируемая система

| ID | Название |
|---|---|
| `gym_aggregator` | ИС-агрегатор фитнес-клубов |

### Роли (5)

| ID | Роль | Локальные ID |
|---|---|---|
| `client` | Клиент | `client`, `visitor` |
| `gym_admin` | Администратор зала | `partner_admin`, `gym_admin`, `club_admin` |
| `platform_operator` | Оператор платформы | `platform_operator`, `platform_admin`, `operator`, `moderator`, `support` |
| `analyst` | Аналитик платформы | `analyst` |
| `devops` | DevOps-инженер | `devops` |

### Внешние системы (7)

| ID | Система | Локальные ID |
|---|---|---|
| `payment_gateway` | Платёжный шлюз | `payment_gateway`, `payment` |
| `maps_service` | Картографический сервис | `maps_service`, `maps` |
| `notification_gateway` | Сервисы доставки уведомлений | `sms_provider`, `push_service`, `notify`, `notify_ext`, `notification_gateway` |
| `access_control` | СКУД и датчики залов | `access_control`, `acs` |
| `idp` | Провайдер идентификации (VK ID, Sber ID) | `idp` |
| `bi_platform` | BI-платформа (Yandex DataLens) | `bi_platform` |
| `accounting_system` | Система бухгалтерского учёта (1С) | `accounting_system` |

Не вошли в сводную схему: веб-аналитика (`web_analytics`, дублирует собственные события и передаёт данные пользователей третьей стороне) и CI/CD (`ci_cd`, система разработки, будет на диаграмме развёртывания).

### Контейнеры (16)

| ID | Название | Стек | Зона |
|---|---|---|---|
| `mobile_app` | Мобильное приложение клиента | React Native / TypeScript | Frontend |
| `admin_web` | Веб-панель администрирования | React 18 / TypeScript, Vite | Frontend |
| `api_gateway` | API-шлюз | Nginx | DevOps |
| `auth_service` | Сервис авторизации | Python 3.12 / FastAPI | Backend |
| `core_api` | Сервис бизнес-логики | Python 3.12 / FastAPI, SQLAlchemy | Backend |
| `integration_service` | Сервис интеграций и уведомлений | Python 3.12 / FastAPI, Celery | Backend |
| `iot_service` | Сервис допуска и загруженности | Python 3.12 / FastAPI, asyncio, aiomqtt | Backend |
| `analytics_service` | Сервис отчётности | Python 3.12 / FastAPI, pandas | Analytics |
| `etl_service` | Сервис загрузки данных (ETL) | Python 3.12 / Apache Airflow, pandas | Analytics |
| `dwh` | Аналитическое хранилище и витрины | ClickHouse | Analytics |
| `message_broker` | Брокер сообщений | RabbitMQ 3 (AMQP) | DevOps |
| `mqtt_broker` | MQTT-брокер | Eclipse Mosquitto 2.0 | DevOps |
| `cache` | Кэш и хранилище сессий | Redis 7 | DevOps |
| `object_storage` | Объектное хранилище | MinIO (S3 API) | DevOps |
| `monitoring` | Система наблюдаемости | Prometheus, Alertmanager, Grafana, Loki | DevOps |
| `database` | Реляционная СУБД | PostgreSQL 16 + PostGIS 3 | Тимлид |

Соответствие локальных ID контейнеров глобальным:

| Было в локальной версии | Стало |
|---|---|
| `partner_web`, `club_web` | `admin_web` |
| `reverse_proxy` | `api_gateway` |
| `api_backend`, `catalog_service`, `booking_service` | `core_api` |
| `notification_service` | `integration_service` |
| `occupancy_service`, `access_service` | `iot_service` |
| `analytics_api` | `analytics_service` |
| `report_storage` | `object_storage` |
| `broker` (RabbitMQ + EMQX в одном контейнере) | `message_broker` и `mqtt_broker` |

### Сетевые порты

| Порт | Протокол | Слушает | Кто инициирует | Доступ |
|---|---|---|---|---|
| 443 | HTTPS / TLS 1.3 | `api_gateway` | `mobile_app`, `admin_web`, `payment_gateway`, `bi_platform` | Интернет |
| 8883 | MQTTS / TLS | `mqtt_broker` | `access_control` | Интернет |
| 8000 | HTTP/JSON | `core_api` | `api_gateway` | Внутренняя сеть |
| 8001 | HTTP/JSON | `auth_service` | `api_gateway` | Внутренняя сеть |
| 8002 | HTTP/JSON | `integration_service` | `api_gateway`, `core_api` | Внутренняя сеть |
| 8003 | HTTP/JSON | `analytics_service` | `api_gateway` | Внутренняя сеть |
| 8004 | HTTP/JSON | `iot_service` | `api_gateway` | Внутренняя сеть |
| 1883 | MQTT / TCP | `mqtt_broker` | `iot_service` | Внутренняя сеть |
| 5672 | AMQP | `message_broker` | `core_api`, `integration_service`, `iot_service`, `analytics_service`, `etl_service` | Внутренняя сеть |
| 5432 | SQL / TCP | `database` | `auth_service`, `core_api`, `integration_service`, `iot_service`, `etl_service` | Сеть БД |
| 6379 | RESP / TCP | `cache` | `auth_service`, `core_api`, `iot_service` | Внутренняя сеть |
| 8123 | HTTP | `dwh` | `analytics_service`, `etl_service`, `api_gateway` (BI) | Внутренняя сеть |
| 9000 | HTTPS (S3 API) | `object_storage` | `core_api`, `analytics_service` | Внутренняя сеть |
| 3000 | HTTPS | `monitoring` (Grafana) | `devops` | Внутренняя сеть, DevOps |
| 9187 | HTTP (`/metrics`) | `database` (postgres_exporter) | `monitoring` | Внутренняя сеть, только для `monitoring` |
| 15692 | HTTP (`/metrics`) | `message_broker` (плагин Prometheus) | `monitoring` | Внутренняя сеть, только для `monitoring` |

Порты 9090 (Prometheus), 9093 (Alertmanager) и 3100 (Loki) используются только внутри стека `monitoring` и в таблицу не вносятся. Порт 465 (SMTP/TLS) принадлежит внешнему почтовому серверу, к которому `monitoring` и `integration_service` подключаются как клиенты.

### Доменные события

События между сервисами идут через RabbitMQ: topic-обменник, у каждого подписчика своя очередь, сообщение упаковано в единый JSON-конверт `EventEnvelope` с `event_id`. Поэтому одно событие получают все подписчики, а повтор подписчик распознаёт по идентификатору. У каждого события один издатель.

| Событие | Издатель | Подписчики | Смысл |
|---|---|---|---|
| `order.created` | `core_api` | `etl_service` | Создан заказ абонемента |
| `payment.succeeded`, `payment.failed`, `payment.refunded` | `integration_service` | `core_api`, `etl_service` | Результат оплаты или возврата по webhook |
| `subscription.activated` | `core_api` | `iot_service`, `integration_service`, `etl_service` | Абонемент оплачен: активировать пропуск, уведомить клиента |
| `subscription.expiring` | `core_api` | `integration_service`, `etl_service` | Напоминание об окончании абонемента |
| `gym.updated` | `core_api` | `iot_service`, `etl_service` | Изменилась карточка зала, в том числе вместимость |
| `access.passed` | `iot_service` | `core_api`, `integration_service`, `etl_service` | Вход или выход (турникет, сканер администратора, ручная отметка) |
| `report.ready` | `analytics_service` | `integration_service`, `etl_service` | Отчёт готов: отправить письмо |

## Глобальный глоссарий компонентов (уровень 3)

Локальные диаграммы компонентов остаются самодостаточными для личной защиты: идентификаторы в `.puml`-файлах участников не меняются. Соответствие локальных идентификаторов глобальным ведётся в таблице ниже, как это сделано для контейнеров, ролей и внешних систем. Сводные материалы и отчёты ссылаются на компоненты только по глобальным ID.

### Правило образования глобального ID

Глобальный ID компонента строится по схеме `<префикс контейнера>_<имя компонента>`.

- Префикс закреплён за контейнером и уникален в проекте (таблица ниже).
- Суффикс `_comp` отбрасывается: префикс уже указывает, что это компонент определённого контейнера.
- Если локальный ID уже начинается с нужного префикса (`mob_ui_shell`, `adm_api_client`, `auth_api`), он сохраняется без изменений.
- Роль компонента читается по окончанию имени: `_api` и `_controller` означают входной контроллер, `_service` означает сервис слоя бизнес-логики, `_repository`, `_client`, `_adapter` и `_event_bus` означают инфраструктурный слой.
- Границы слоёв получают идентификаторы вида `<префикс>_layer_api`, `<префикс>_layer_service`, `<префикс>_layer_infra`. У фронтенда остаются `mob_layer_*` и `adm_layer_*`. Так устраняются совпадения `api_layer` и `service_layer` в `core_api`, `integration_service` и `iot_service`.

### Префиксы контейнеров и локальные диаграммы

| Контейнер | Префикс | Автор | Файл диаграммы | Компонентов |
|---|---|---|---|---|
| `mobile_app` | `mob_` | Осипов Илья | `L3_frontend_mobile_app.puml` | 9 |
| `admin_web` | `adm_` | Осипов Илья | `L3_frontend_admin_web.puml` | 9 |
| `api_gateway` | `gw_` | Дамакальщиков Михаил | `L3_devops_api_gateway.puml` | 6 |
| `auth_service` | `auth_` | Кутенков Сергей | `L3_backend_auth.puml` | 10 |
| `core_api` | `core_` | Кутенков Сергей | `L3_backend_core_api.puml` | 16 |
| `integration_service` | `int_` | Лисов Матфей | `L3_1_teamlead.puml` | 12 |
| `iot_service` | `iot_` | Лисов Матфей | `L3_2_teamlead.puml` | 8 |
| `analytics_service` | `rep_` | Эрендженова Мария | `L3_reporting_analyst.puml` | 7 |
| `etl_service` | `etl_` | Эрендженова Мария | `L3_etl_analyst.puml` | 6 |
| `monitoring` | `mon_` | Дамакальщиков Михаил | `L3_devops_monitoring.puml` | 7 |
| Итого | | | | 90 |

Файлы лежат в папках участников внутри `src/local/`.

### Компоненты (90)

Столбец «Слой / группа» показывает слой по локальной диаграмме. У `api_gateway`, `analytics_service`, `etl_service` и `monitoring` границы слоёв на диаграмме не нарисованы, поэтому группы выведены из назначения компонентов. Столбец «Изменение»: «новый» — добавлен при согласовании перед ЛР3, «переименован» — изменено название (ID прежний), «L4» — компонент детализирован диаграммой кода. Удалён компонент `core_iot_adapter` (локальный `iot_adapter`, «Адаптер СКУД»): связи `core_api` → `iot_service` больше нет.

| Контейнер | Слой / группа | Локальный ID | Глобальный ID | Название | Изменение |
|---|---|---|---|---|---|
| `mobile_app` | Представление | `mob_ui_shell` | `mob_ui_shell` | UI-слой и навигация |  |
| `mobile_app` | Прикладная логика | `mob_catalog_controller` | `mob_catalog_controller` | Контроллер каталога и геопоиска |  |
| `mobile_app` | Прикладная логика | `mob_purchase_controller` | `mob_purchase_controller` | Контроллер покупки абонемента |  |
| `mobile_app` | Прикладная логика | `mob_pass_service` | `mob_pass_service` | Сервис электронного пропуска |  |
| `mobile_app` | Прикладная логика | `mob_session_service` | `mob_session_service` | Сервис сессии и авторизации |  |
| `mobile_app` | Доступ к данным и интеграции | `mob_api_client` | `mob_api_client` | Клиент API-шлюза |  |
| `mobile_app` | Доступ к данным и интеграции | `mob_secure_store` | `mob_secure_store` | Локальное защищённое хранилище |  |
| `mobile_app` | Доступ к данным и интеграции | `mob_payment_adapter` | `mob_payment_adapter` | Адаптер платёжного SDK |  |
| `mobile_app` | Доступ к данным и интеграции | `mob_push_handler` | `mob_push_handler` | Обработчик push-уведомлений |  |
| `admin_web` | Представление | `adm_ui_shell` | `adm_ui_shell` | Каркас SPA и навигация |  |
| `admin_web` | Прикладная логика | `adm_auth_service` | `adm_auth_service` | Сервис сессии и разграничения прав |  |
| `admin_web` | Прикладная логика | `adm_gym_profile_controller` | `adm_gym_profile_controller` | Контроллер карточки зала |  |
| `admin_web` | Прикладная логика | `adm_moderation_controller` | `adm_moderation_controller` | Контроллер модерации и обращений |  |
| `admin_web` | Прикладная логика | `adm_report_controller` | `adm_report_controller` | Контроллер отчётности |  |
| `admin_web` | Доступ к данным и интеграции | `adm_api_client` | `adm_api_client` | Клиент API-шлюза |  |
| `admin_web` | Доступ к данным и интеграции | `adm_file_service` | `adm_file_service` | Сервис файловых операций |  |
| `admin_web` | Доступ к данным и интеграции | `adm_state_store` | `adm_state_store` | Клиентское состояние и кэш |  |
| `admin_web` | Прикладная логика | `adm_access_controller` | `adm_access_controller` | Контроллер допуска | новый, L4 |
| `api_gateway` | Входной контур | `tls_comp` | `gw_tls` | Модуль проверки TLS-сертификата |  |
| `api_gateway` | Входной контур | `ratelimit_comp` | `gw_ratelimit` | Модуль ограничения нагрузки | L4 |
| `api_gateway` | Контроль доступа | `authcheck_comp` | `gw_authcheck` | Модуль проверки доступа |  |
| `api_gateway` | Контроль доступа | `partner_comp` | `gw_partner` | Модуль доступа внешних систем |  |
| `api_gateway` | Маршрутизация | `router_comp` | `gw_router` | Модуль маршрутизации |  |
| `api_gateway` | Наблюдаемость | `metrics_comp` | `gw_metrics` | Модуль метрик |  |
| `auth_service` | API | `auth_api` | `auth_api` | API аутентификации |  |
| `auth_service` | API | `oauth_api` | `auth_oauth_api` | API внешнего входа (SSO) |  |
| `auth_service` | API | `user_api` | `auth_user_api` | API профилей |  |
| `auth_service` | Бизнес-логика | `auth_service_logic` | `auth_authn_service` | Сервис аутентификации |  |
| `auth_service` | Бизнес-логика | `oauth_service` | `auth_oauth_service` | Сервис OAuth 2.0 |  |
| `auth_service` | Бизнес-логика | `user_service` | `auth_user_service` | Сервис пользователей |  |
| `auth_service` | Бизнес-логика | `session_service` | `auth_session_service` | Сервис сессий |  |
| `auth_service` | Инфраструктура | `db_repository` | `auth_db_repository` | Репозиторий пользователей |  |
| `auth_service` | Инфраструктура | `cache_repository` | `auth_cache_repository` | Репозиторий сессий |  |
| `auth_service` | Инфраструктура | `idp_adapter` | `auth_idp_adapter` | Адаптер провайдера (IdP) |  |
| `core_api` | API | `catalog_api` | `core_catalog_api` | API каталога и отзывов | переименован |
| `core_api` | API | `booking_api` | `core_booking_api` | API заказов и абонементов | переименован |
| `core_api` | API | `payment_api` | `core_payment_api` | API оплаты заказа | переименован |
| `core_api` | API | `admin_tariff_api` | `core_admin_tariff_api` | API тарифов и условий размещения | переименован |
| `core_api` | Бизнес-логика | `booking_service` | `core_booking_service` | Сервис абонементов | переименован |
| `core_api` | Бизнес-логика | `tariff_service` | `core_tariff_service` | Сервис тарификации | L4 |
| `core_api` | Бизнес-логика | `payment_service` | `core_payment_service` | Сервис оплат |  |
| `core_api` | Инфраструктура | `db_repository` | `core_db_repository` | Репозиторий БД |  |
| `core_api` | Инфраструктура | `integration_adapter` | `core_integration_adapter` | Адаптер сервиса интеграций | переименован |
| `core_api` | API | `gym_profile_api` | `core_gym_profile_api` | API кабинета зала | новый |
| `core_api` | API | `moderation_api` | `core_moderation_api` | API модерации и обращений | новый |
| `core_api` | Бизнес-логика | `catalog_service` | `core_catalog_service` | Сервис каталога | новый |
| `core_api` | Бизнес-логика | `moderation_service` | `core_moderation_service` | Сервис модерации | новый |
| `core_api` | Инфраструктура | `cache_adapter` | `core_cache_adapter` | Адаптер кэша | новый |
| `core_api` | Инфраструктура | `photo_storage_adapter` | `core_photo_storage_adapter` | Адаптер хранилища фотографий | новый |
| `core_api` | Инфраструктура | `event_bus` | `core_event_bus` | Шина событий | новый |
| `integration_service` | API | `webhook_api_comp` | `int_webhook_api` | Контроллер webhook платёжной системы |  |
| `integration_service` | API | `integration_api_comp` | `int_internal_api` | Контроллер внутренних запросов |  |
| `integration_service` | Бизнес-логика | `payment_comp` | `int_payment_service` | Платёжный сервис |  |
| `integration_service` | Бизнес-логика | `payout_comp` | `int_payout_service` | Сервис выплат залам |  |
| `integration_service` | Бизнес-логика | `geocoding_comp` | `int_geocoding_service` | Сервис геокодирования |  |
| `integration_service` | Бизнес-логика | `notification_comp` | `int_notification_service` | Сервис уведомлений |  |
| `integration_service` | Инфраструктура | `acquiring_client_comp` | `int_acquiring_client` | Клиент платёжного шлюза |  |
| `integration_service` | Инфраструктура | `maps_client_comp` | `int_maps_client` | Клиент картографического сервиса |  |
| `integration_service` | Инфраструктура | `delivery_client_comp` | `int_delivery_client` | Клиент провайдеров доставки |  |
| `integration_service` | Инфраструктура | `integration_repo_comp` | `int_repository` | Репозиторий платежей и журнала обмена |  |
| `integration_service` | Инфраструктура | `integration_events_comp` | `int_event_bus` | Шина событий |  |
| `integration_service` | API | `device_api_comp` | `int_device_api` | Контроллер регистрации устройств | новый |
| `iot_service` | API | `iot_api_comp` | `iot_api` | Контроллер допуска | переименован |
| `iot_service` | Бизнес-логика | `pass_comp` | `iot_pass_service` | Сервис QR-пропусков |  |
| `iot_service` | Бизнес-логика | `access_comp` | `iot_access_service` | Сервис допуска |  |
| `iot_service` | Бизнес-логика | `occupancy_comp` | `iot_occupancy_service` | Сервис индекса загруженности | L4 |
| `iot_service` | Инфраструктура | `mqtt_gateway_comp` | `iot_mqtt_client` | Клиент MQTT-брокера |  |
| `iot_service` | Инфраструктура | `iot_repo_comp` | `iot_repository` | Репозиторий учёта посещений и истории загруженности | переименован |
| `iot_service` | Инфраструктура | `iot_cache_comp` | `iot_cache_client` | Клиент кэша |  |
| `iot_service` | Инфраструктура | `iot_events_comp` | `iot_event_bus` | Шина событий |  |
| `analytics_service` | API | `report_controller` | `rep_controller` | Контроллер отчётности |  |
| `analytics_service` | Бизнес-логика | `metrics_engine` | `rep_metrics_engine` | Модуль расчёта показателей |  |
| `analytics_service` | Бизнес-логика | `report_builder` | `rep_report_builder` | Сборщик отчётов |  |
| `analytics_service` | Бизнес-логика | `settlement_exporter` | `rep_settlement_exporter` | Модуль реестров начислений |  |
| `analytics_service` | Инфраструктура | `mart_repository` | `rep_mart_repository` | Репозиторий витрин |  |
| `analytics_service` | Инфраструктура | `storage_gateway` | `rep_storage_gateway` | Шлюз файлового хранилища |  |
| `analytics_service` | Инфраструктура | `event_publisher` | `rep_event_publisher` | Издатель событий |  |
| `etl_service` | Оркестрация | `dag_scheduler` | `etl_dag_scheduler` | Планировщик загрузок |  |
| `etl_service` | Извлечение | `db_extractor` | `etl_db_extractor` | Экстрактор справочников и реестра выплат | переименован |
| `etl_service` | Извлечение | `event_consumer` | `etl_event_consumer` | Потребитель потока событий |  |
| `etl_service` | Преобразование и контроль качества | `transform_engine` | `etl_transform_engine` | Модуль преобразования |  |
| `etl_service` | Преобразование и контроль качества | `dq_validator` | `etl_dq_validator` | Модуль контроля качества данных | L4 |
| `etl_service` | Загрузка | `mart_loader` | `etl_mart_loader` | Загрузчик витрин |  |
| `monitoring` | Сбор | `scrape_comp` | `mon_scraper` | Сборщик метрик |  |
| `monitoring` | Хранение | `tsdb_comp` | `mon_tsdb` | Хранилище метрик |  |
| `monitoring` | Оповещения | `rules_comp` | `mon_rules` | Движок правил оповещений |  |
| `monitoring` | Оповещения | `alert_comp` | `mon_alerting` | Маршрутизатор оповещений |  |
| `monitoring` | Сбор | `log_agent` | `mon_log_agent` | Агент сбора логов |  |
| `monitoring` | Хранение | `logs_comp` | `mon_log_store` | Хранилище логов |  |
| `monitoring` | Визуализация | `viz_comp` | `mon_dashboards` | Панели визуализации |  |

### Стыковочные шлюзы контейнеров

Стыковочным шлюзом называется компонент, на который в локальной диаграмме приходит сетевая стрелка из другого контейнера, внешней системы или роли. На уровне 2 такая стрелка ведёт в контейнер как в чёрный ящик, на уровне 3 она уточняется до конкретного шлюза. Контейнеру разрешено иметь несколько шлюзов, если у входов разные инициаторы или разные предметные области.

| Контейнер | Шлюз (глобальный ID) | Протокол и порт | Кто обращается (инициатор) |
|---|---|---|---|
| `mobile_app` | `mob_ui_shell` | Android / iOS | `client` |
| `mobile_app` | `mob_push_handler` | FCM / APNs | `notification_gateway` |
| `admin_web` | `adm_ui_shell` | HTTPS | `analyst`, `gym_admin`, `platform_operator` |
| `api_gateway` | `gw_tls` | HTTPS/JSON (REST), TCP 443; HTTPS/JSON, TCP 443; SQL over HTTPS, TCP 443 | `admin_web`, `bi_platform`, `mobile_app`, `payment_gateway` |
| `api_gateway` | `gw_metrics` | HTTP GET /metrics | `monitoring` |
| `auth_service` | `auth_api` | HTTP GET /metrics; HTTP/JSON, TCP 8001 | `api_gateway`, `monitoring` |
| `auth_service` | `auth_oauth_api` | HTTP/JSON, TCP 8001 | `api_gateway` |
| `auth_service` | `auth_user_api` | HTTP/JSON, TCP 8001 | `api_gateway` |
| `core_api` | `core_catalog_api` | HTTP GET /metrics; HTTP/JSON, TCP 8000 | `api_gateway`, `monitoring` |
| `core_api` | `core_gym_profile_api` | HTTP/JSON, TCP 8000 | `api_gateway` |
| `core_api` | `core_admin_tariff_api` | HTTP/JSON, TCP 8000 | `api_gateway` |
| `core_api` | `core_booking_api` | HTTP/JSON, TCP 8000 | `api_gateway` |
| `core_api` | `core_payment_api` | HTTP/JSON, TCP 8000 | `api_gateway` |
| `core_api` | `core_moderation_api` | HTTP/JSON, TCP 8000 | `api_gateway` |
| `integration_service` | `int_webhook_api` | HTTP/JSON, TCP 8002 | `api_gateway` |
| `integration_service` | `int_device_api` | HTTP/JSON, TCP 8002 | `api_gateway` |
| `integration_service` | `int_internal_api` | HTTP GET /metrics; HTTP/JSON, TCP 8002 | `core_api`, `monitoring` |
| `iot_service` | `iot_api` | HTTP GET /metrics; HTTP/JSON, TCP 8004 | `api_gateway`, `monitoring` |
| `analytics_service` | `rep_controller` | HTTP GET /metrics; HTTP/JSON, TCP 8003 | `api_gateway`, `monitoring` |
| `monitoring` | `mon_dashboards` | HTTPS, TCP 3000 | `devops` |
| `etl_service` | нет | нет | Запуск по расписанию внутри контейнера, входящих сетевых вызовов нет |

### Связи между контейнерами

Сверка ведётся со стороны инициатора: берётся исходящая стрелка в диаграмме инициатора, затем в диаграмме приёмника ищется шлюз с тем же протоколом и портом. Все 17 связей совпадают. Чтение журналов шлюза (`mon_log_agent` → `api_gateway`, Docker Engine API, stdout) не является сетевым вызовом компонента и шлюза-приёмника не требует.

| № | Инициатор | Компонент-инициатор | Приёмник | Компонент-приёмник (шлюз) | Протокол и порт |
|---|---|---|---|---|---|
| 1 | `core_api` | `core_integration_adapter` | `integration_service` | `int_internal_api` | HTTP/JSON, TCP 8002 |
| 2 | `monitoring` | `mon_scraper` | `api_gateway` | `gw_metrics` | HTTP GET /metrics |
| 3 | `notification_gateway` | (внешняя система) | `mobile_app` | `mob_push_handler` | FCM / APNs |
| 4 | `mobile_app` | `mob_api_client` | `api_gateway` | `gw_tls` | HTTPS/JSON (REST), TCP 443 |
| 5 | `admin_web` | `adm_api_client` | `api_gateway` | `gw_tls` | HTTPS/JSON (REST), TCP 443 |
| 6 | `payment_gateway` | (внешняя система) | `api_gateway` | `gw_tls` | HTTPS/JSON, TCP 443 |
| 7 | `bi_platform` | (внешняя система) | `api_gateway` | `gw_tls` | SQL over HTTPS, TCP 443 |
| 8 | `api_gateway` | `gw_authcheck`, `gw_router` | `auth_service` | `auth_api`, `auth_oauth_api`, `auth_user_api` | HTTP/JSON, TCP 8001 |
| 9 | `api_gateway` | `gw_router` | `core_api` | `core_admin_tariff_api`, `core_booking_api`, `core_catalog_api`, `core_gym_profile_api`, `core_moderation_api`, `core_payment_api` | HTTP/JSON, TCP 8000 |
| 10 | `api_gateway` | `gw_partner`, `gw_router` | `integration_service` | `int_device_api`, `int_webhook_api` | HTTP/JSON, TCP 8002 |
| 11 | `api_gateway` | `gw_router` | `analytics_service` | `rep_controller` | HTTP/JSON, TCP 8003 |
| 12 | `api_gateway` | `gw_router` | `iot_service` | `iot_api` | HTTP/JSON, TCP 8004 |
| 13 | `monitoring` | `mon_scraper` | `core_api` | `core_catalog_api` | HTTP GET /metrics |
| 14 | `monitoring` | `mon_scraper` | `integration_service` | `int_internal_api` | HTTP GET /metrics |
| 15 | `monitoring` | `mon_scraper` | `auth_service` | `auth_api` | HTTP GET /metrics |
| 16 | `monitoring` | `mon_scraper` | `iot_service` | `iot_api` | HTTP GET /metrics |
| 17 | `monitoring` | `mon_scraper` | `analytics_service` | `rep_controller` | HTTP GET /metrics |

### Связи компонентов с хранилищами, брокерами и внешними системами

Исходящие сетевые вызовы к хранилищам, брокерам и внешним системам идут только из компонентов инфраструктурного слоя (репозитории, клиенты, адаптеры, шины событий).

| Компонент-инициатор | Приёмник | Протокол и порт | Назначение связи |
|---|---|---|---|
| `mob_ui_shell` | `maps_service` | HTTPS/JSON | Загружает тайлы карты и строит маршрут до зала |
| `mob_payment_adapter` | `payment_gateway` | HTTPS/JSON, SDK | Передаёт данные карты в токенизированном виде через платёжный SDK |
| `gw_partner` | `dwh` | HTTP, TCP 8123 | Проксирует запросы BI к витринам (только чтение) |
| `auth_db_repository` | `database` | SQL/TCP, TCP 5432 | Читает и записывает профили пользователей и роли |
| `auth_cache_repository` | `cache` | RESP/TCP, TCP 6379 | Хранит активные сессии и выпущенные токены |
| `auth_idp_adapter` | `idp` | HTTPS, OAuth 2.0 / OIDC | Обменивает код авторизации на подтверждённый профиль |
| `core_db_repository` | `database` | SQL/TCP, TCP 5432 | Читает и записывает каталог, тарифы, условия и комиссии, абонементы, заказы, отзывы, выполняет геозапросы |
| `core_cache_adapter` | `cache` | RESP/TCP, TCP 6379 | Кэширует геопоиск, читает индекс загруженности |
| `core_photo_storage_adapter` | `object_storage` | HTTPS (S3 API), TCP 9000 | Сохраняет и отдаёт фотографии залов |
| `core_event_bus` | `message_broker` | AMQP, TCP 5672 | Публикует `order.created`, `subscription.activated`, `subscription.expiring`, `gym.updated`; получает `payment.*`, `access.passed` |
| `int_acquiring_client` | `payment_gateway` | HTTPS/REST | Создаёт платежи, оформляет возвраты и выплаты залам |
| `int_maps_client` | `maps_service` | HTTPS/REST | Геокодирует адреса залов |
| `int_delivery_client` | `notification_gateway` | HTTPS/REST, SMTP/TLS 465 | Отправляет push, SMS и e-mail на доставку |
| `int_repository` | `database` | SQL/TCP, TCP 5432 | Пишет статусы платежей, реестр выплат залам, токены устройств и журнал обмена |
| `int_event_bus` | `message_broker` | AMQP, TCP 5672 | Публикует `payment.*`; получает `subscription.*`, `access.passed`, `report.ready` для уведомлений |
| `iot_mqtt_client` | `mqtt_broker` | MQTT / TCP, порт 1883, внутренняя сеть | Подписывается на топики `gym/{gym_id}/access`, публикует команды допуска |
| `iot_repository` | `database` | SQL/TCP, TCP 5432 | Ведёт учёт посещений (входы и выходы от турникета, сканера и ручных отметок) и историю загруженности |
| `iot_cache_client` | `cache` | RESP/TCP, TCP 6379 | Публикует индекс загруженности, хранит токены пропусков |
| `iot_event_bus` | `message_broker` | AMQP, TCP 5672 | Публикует `access.passed`; получает `subscription.activated`, `gym.updated` |
| `rep_mart_repository` | `dwh` | HTTP, TCP 8123 | Выполняет аналитические запросы к витринам |
| `rep_storage_gateway` | `object_storage` | HTTPS (S3 API), TCP 9000 | Сохраняет и отдаёт файлы отчётов |
| `rep_event_publisher` | `message_broker` | AMQP, TCP 5672 | Публикует `report.ready` |
| `rep_settlement_exporter` | `accounting_system` | HTTPS/REST, XML | Передаёт реестры начислений и акты по залам |
| `etl_db_extractor` | `database` | SQL/TCP, TCP 5432 | Инкрементально выгружает справочники и реестр выплат |
| `etl_event_consumer` | `message_broker` | AMQP, TCP 5672 | Получает доменные события из собственной очереди |
| `etl_mart_loader` | `dwh` | HTTP, TCP 8123 | Загружает очищенные данные и пересчитывает витрины |
| `etl_dag_scheduler` | `dwh` | HTTP, TCP 8123 | Читает метки инкремента, пишет статус запуска в журнал загрузок |
| `mon_scraper` | `database` | HTTP GET /metrics, TCP 9187 | Опрашивает метрики СУБД |
| `mon_scraper` | `message_broker` | HTTP GET /metrics, TCP 15692 | Опрашивает метрики очередей |
| `mon_alerting` | `notification_gateway` | SMTP/TLS, TCP 465 | Отправляет оповещения об инцидентах напрямую, минуя сервис интеграций |

## Уровень 4: диаграммы кода

Каждый участник детализировал один компонент своего контейнера до кода. Код, README и диаграммы L4 используют глобальные ID компонентов; в заголовке каждой L4 указан и локальный ID из L3 автора («на L3 — …»).

| Автор | Контейнер | Компонент (глобальный ID = пакет кода) | Локальный ID на L3 | Язык | Шаблон «Стратегия» |
|---|---|---|---|---|---|
| Лисов Матфей | `iot_service` | `iot_occupancy_service` | `occupancy_comp` | Python 3.12 | Подсчёт посетителей: `exact_balance`, `visit_timeout`, `smoothed_*`; стратегия своя у каждого зала |
| Кутенков Сергей | `core_api` | `core_tariff_service` | `tariff_service` | Python 3.12 | Цена: `standard`, `promo_code`, `first_purchase`; комиссия: `percentage`, `percentage_with_minimum`, `subscription_plan` |
| Эрендженова Мария | `etl_service` | `etl_dq_validator` | `dq_validator` | Python 3.12, pandas | Правила качества (8 правил); политика отбраковки: `strict_batch`, `quarantine_rows`, `audit_only` |
| Дамакальщиков Михаил | `api_gateway` | `gw_ratelimit` | `ratelimit_comp` | TypeScript → njs (Nginx) | Алгоритм: `fixed_window`, `sliding_window`, `token_bucket`; ключ клиента: `ip`, `bearer_token` |
| Осипов Илья | `admin_web` | `adm_access_controller` | `adm_access_controller` | TypeScript (React, Redux) | Режим отметки: `scan`, `manual`; доставка: `online_only`, `queue_exits_offline` |

### Общие контракты

Типы данных на границах контейнеров не описываются каждым участником заново, а берутся из пакета `src/local/L4/contracts/`:

- `python/fitagg_contracts` — Python-пакет на pydantic v2: `events.py` (конверт `EventEnvelope` и события каталога), `http.py` (`PaymentSplit`, `AdminAccessMarkRequest`, `AccessMarkResult`, `RateLimitedError`), `money.py` (сумма в копейках);
- `ts/contracts.ts` — зеркало HTTP-контрактов на TypeScript для `admin_web` и `api_gateway`; имена полей совпадают с Python (snake_case).

Контракты неизменяемы и проверяют инварианты стыка сами: например, в `PaymentSplit` доля зала и комиссия всегда в сумме дают итог. Паттерны компонентов независимы: общих базовых классов стратегий нет, общие только эти типы данных.

### Проверки интеграции

Скрипты лежат в `src/local/L4/integration/` и запускаются из папки `src/local/L4`.

| Проверка | Команда | Что проверяет |
|---|---|---|
| Диаграмма ↔ код | `python integration/check_diagram_code.py` | В обе стороны: всё с диаграммы есть в коде и все классы кода есть на диаграмме; глобальный и локальный ID в заголовке; условные обозначения |
| Контракты TS ↔ Python | `python integration/check_contracts.py` | Имена полей и значения перечислений; образцы, собранные кодом на TypeScript, проходят модели pydantic (нужны Node.js и esbuild) |
| Аннотации типов | `python integration/check_annotations.py <папки>` | У каждой функции аннотированы параметры и возвращаемое значение |

### Как запустить компонент

| Компонент | Папка | Команды |
|---|---|---|
| `iot_occupancy_service` | `src/local/L4/lisov/iot_occupancy_service` | `pip install pydantic`, `python demo.py` |
| `core_tariff_service` | `src/local/L4/kutenkov/core_tariff_service` | `pip install pydantic`, `python demo.py` |
| `etl_dq_validator` | `src/local/L4/erendzhenova/etl_dq_validator` | `pip install pydantic pandas`, `python demo.py` |
| `gw_ratelimit` | `src/local/L4/damakalshchikov/gw_ratelimit` | `npm install`, `npm test`, `npm run build` |
| `adm_access_controller` | `src/local/L4/osipov/adm_access_controller` | `npm install`, `npm test` |

Тесты Python-компонентов запускаются командой `python -m pytest` (нужен `pytest`), проверка типов — `mypy` (строгий режим задан в `pyproject.toml`). У TypeScript-компонентов проверка типов — `npm run typecheck`.

## Структура репозитория

```
.
├── README.md
├── .gitignore
├── .github/                       # workflow сборки диаграмм (CI/CD)
├── docs/
│   ├── images/
│   │   ├── main_context.png       # сводная диаграмма контекста (C4, уровень 1)
│   │   ├── main_context.svg
│   │   ├── main_containers.png    # сводная диаграмма контейнеров (C4, уровень 2)
│   │   ├── main_containers.svg
│   │   └── local/                 # изображения локальных диаграмм участников
│   └── reports/                   # отчёты по лабораторным и курсовой работе
└── src/
    ├── main_context.puml          # исходник сводной диаграммы контекста
    ├── main_containers.puml       # исходник сводной диаграммы контейнеров
    ├── integrations/              # материалы интеграции локальных представлений
    └── local/
        ├── lisov/                 # локальные диаграммы участников (L1, L2, L3)
        ├── kutenkov/
        ├── Osipov_Ilya/
        ├── erenmari/
        ├── damakalshchikov/
        └── L4/                    # уровень 4: диаграммы кода и код компонентов
            ├── contracts/         # общие типы на стыках (Python и TypeScript)
            ├── integration/       # скрипты проверок интеграции
            ├── lisov/iot_occupancy_service/
            ├── kutenkov/core_tariff_service/
            ├── erendzhenova/etl_dq_validator/
            ├── damakalshchikov/gw_ratelimit/
            └── osipov/adm_access_controller/
```

В папке каждого компонента уровня 4: `diagram/` (диаграмма классов `.puml` и `.png`), `src/` (код), `demo.py` или `tests/`, `README.md`.

## Как собрать диаграммы

**Локально в VS Code.** Установите расширение «PlantUML», откройте нужный `.puml` и нажмите `Alt+D` для предпросмотра. Для отрисовки нужен Graphviz. Можно запустить локальный PlantUML Server в Docker, чтобы исходный код схем не уходил на публичные серверы.

**В CI.** Workflow из `.github/` собирает `.puml` из `src/` в изображения и кладёт их в `docs/images/` при каждом изменении в `main`.

## Правила оформления диаграмм

- Для связей используется только макрос `Rel(от, кому, "описание", "протокол")`. Макросы жёсткого позиционирования (`Rel_D`, `Rel_L`, `Rel_R`, `Rel_U`) запрещены.
- У каждой связи есть описание бизнес-действия и технический протокол (например, `HTTPS/JSON`, `SQL/TCP 5432`).
- Стрелка показывает инициатора сетевой сессии.
- Стили и `skinparam` допускаются только в главном файле.
- На диаграммах уровня 3 вызовы между компонентами одного контейнера подписываются как внутрипроцессные (`Python Call`, `TypeScript Call`). Сетевой протокол с портом указывается только у стрелок, которые выходят за границу контейнера.
- В сервисных контейнерах с тремя слоями сетевые вызовы наружу выполняют компоненты инфраструктурного слоя (клиенты, адаптеры, репозитории, шины событий), а компоненты слоя API и слоя бизнес-логики обращаются к внешним системам через них. Исключения автор оговаривает в обосновании своей диаграммы.
- Входящие сетевые вызовы принимают стыковочные шлюзы контейнера. Новый входящий вызов добавляется вместе со строкой в таблице шлюзов.
- Компонент, добавленный в локальную диаграмму, вносится в таблицу «Компоненты» с глобальным ID по правилу образования ID. Идентификаторы в локальных файлах при этом не переименовываются.
- Все участники используют единые глобальные ID из глоссария (`client`, `gym_admin`, `platform_operator`, `mobile_app`, `admin_web`, `api_gateway`, `database`, `iot_service`, `payment_gateway`, `access_control` и другие); соответствие локальных ID глобальным приведено в разделе «Глобальный глоссарий ID».
- Диаграмма уровня 4 — UML-диаграмма классов функционального компонента. В её заголовке указаны глобальный ID компонента и локальный ID из L3 автора («на L3 — …»), на диаграмме есть условные обозначения (`legend`). Классы и методы диаграммы совпадают с кодом в обе стороны.
- Код уровня 4 использует глобальные ID: имя пакета совпадает с глобальным ID компонента. Порты на диаграмме подписываются глобальными ID компонентов, которые их реализуют (`iot_repository`, `adm_api_client` и т. д.).
- Сообщения на стыках контейнеров типизируются только через `contracts`. Новое поле на стыке добавляется в обе версии контракта (Python и TypeScript) одним Pull Request.

## Процесс работы

Каждый участник работает в своей ветке и вносит изменения в свою зону через Pull Request. Тимлид в роли Enterprise-архитектора проводит обязательное ревью перед слиянием в `main`. Чтобы слияние без ревью было невозможно, для ветки `main` включается правило «Require a pull request review before merging» (Settings → Branches). История коммитов отражает вклад каждого участника.

Чек-лист ревью Pull Request'а с кодом уровня 4:

1. Диаграмма L4 совпадает с кодом (`check_diagram_code.py`), в заголовке глобальный и локальный ID, есть условные обозначения.
2. Стратегия подменяется без правки контекста (есть тест подмены).
3. Строгая типизация: `mypy --strict` или `tsc` в строгом режиме без ошибок.
4. Сообщения на стыке взяты из `contracts`, а не описаны заново (`check_contracts.py`).
5. Внутренняя структура не нарушает контракт с соседним контейнером: ни одна стратегия не меняет поля и инварианты стыка.
6. Паттерн не навязывает ограничений другим контейнерам: нет общих базовых классов стратегий и импорта чужих пакетов.
7. В коммит не попали служебные файлы (`__pycache__/`, `node_modules/`, `build/`).
