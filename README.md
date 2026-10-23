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
| Лисов Матфей | Тимлид | Общая архитектура, сводные диаграммы, глоссарий ID, СУБД, ревью Pull Request'ов |
| Осипов Илья | Frontend | Мобильное приложение, веб-панель, вход через провайдера идентификации, QR-пропуск |
| Кутенков Сергей | Backend | Сервисы авторизации, бизнес-логики, допуска и загруженности, контур СКУД (MQTT) |
| Эренедженова Мария | Аналитик | Сервис отчётности, ETL, ClickHouse, интеграции с BI-платформой и 1С |
| Дамакальщиков Михаил | DevOps | API-шлюз, брокеры, кэш, объектное хранилище, наблюдаемость, CI/CD |

## Архитектура (C4)

Архитектура описана в PlantUML по модели C4.

**Уровень 1, контекст.** Система как чёрный ящик, пять ролей и семь внешних систем: платёжный шлюз, картографический сервис, сервисы доставки уведомлений, СКУД и датчики залов, провайдер идентификации (VK ID, Sber ID), BI-платформа (Yandex DataLens), система бухгалтерского учёта (1С).

**Уровень 2, контейнеры.** Шестнадцать контейнеров, закреплённых за зонами участников. Архитектура сервисная: сервисы независимо разворачиваются и общаются через API и брокеры, но пять из них используют одну общую PostgreSQL.

Наружу открыты только порты 443 (API-шлюз) и 8883 (MQTT-брокер для СКУД), остальное во внутренней сети.

**Уровень 3, компоненты.** Для десяти контейнеров, в которых команда пишет или настраивает собственную логику, построены диаграммы компонентов: `mobile_app`, `admin_web`, `api_gateway`, `auth_service`, `core_api`, `integration_service`, `iot_service`, `analytics_service`, `etl_service`, `monitoring`. Всего на них 82 компонента. Для шести контейнеров (`database`, `cache`, `object_storage`, `dwh`, `message_broker`, `mqtt_broker`) диаграммы компонентов не строятся: это готовые хранилища и брокеры, и в диаграммах уровня 3 они показаны чёрными ящиками. Диаграммы уровня 3 остаются локальными, в одну сводную схему они не собираются: 82 компонента на одном рисунке нечитаемы. Стыковка уровней 2 и 3 ведётся таблицами в разделе «Глобальный глоссарий компонентов».

### Технологический стек

| Узел | Технология |
|---|---|
| Серверная часть | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Celery |
| Мобильное приложение | React Native, TypeScript |
| Веб-панель | React 18, TypeScript, Vite |
| API-шлюз | Nginx |
| База данных | PostgreSQL 16 + PostGIS 3 |
| Кэш и сессии | Redis 7 |
| Брокеры | RabbitMQ 3 (AMQP), Eclipse Mosquitto 2.0 (MQTT) |
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

| Порт | Протокол | Слушает | Доступ |
|---|---|---|---|
| 443 | HTTPS / TLS 1.3 | `api_gateway` | Интернет |
| 8883 | MQTTS / TLS | `mqtt_broker` | Интернет |
| 8000 | HTTP/JSON | `core_api` | Внутренняя сеть |
| 8001 | HTTP/JSON | `auth_service` | Внутренняя сеть |
| 8002 | HTTP/JSON | `integration_service` | Внутренняя сеть |
| 8003 | HTTP/JSON | `analytics_service` | Внутренняя сеть |
| 8004 | HTTP/JSON | `iot_service` | Внутренняя сеть |
| 1883 | MQTT / TCP | `mqtt_broker` | Внутренняя сеть |
| 5672 | AMQP | `message_broker` | Внутренняя сеть |
| 5432 | SQL / TCP | `database` | Сеть БД |
| 6379 | RESP / TCP | `cache` | Внутренняя сеть |
| 8123 | HTTP | `dwh` | Внутренняя сеть |
| 9000 | HTTPS (S3 API) | `object_storage` | Внутренняя сеть |
| 3000 | HTTPS | `monitoring` (Grafana) | Внутренняя сеть, DevOps |
| 9187 | HTTP (`/metrics`) | `database` (postgres_exporter) | Внутренняя сеть, только для `monitoring` |
| 15692 | HTTP (`/metrics`) | `message_broker` (плагин Prometheus) | Внутренняя сеть, только для `monitoring` |

Порты 9090 (Prometheus), 9093 (Alertmanager) и 3100 (Loki) используются только внутри стека `monitoring` и в таблицу не вносятся. Порт 465 (SMTP/TLS) принадлежит внешнему почтовому серверу, к которому `monitoring` и `integration_service` подключаются как клиенты.

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
| `admin_web` | `adm_` | Осипов Илья | `L3_frontend_admin_web.puml` | 8 |
| `api_gateway` | `gw_` | Дамакальщиков Михаил | `L3_devops_api_gateway.puml` | 6 |
| `auth_service` | `auth_` | Кутенков Сергей | `L3_backend_auth.puml` | 10 |
| `core_api` | `core_` | Кутенков Сергей | `L3_backend_core_api.puml` | 10 |
| `integration_service` | `int_` | Лисов Матфей | `L3_1_teamlead.puml` | 11 |
| `iot_service` | `iot_` | Лисов Матфей | `L3_2_teamlead.puml` | 8 |
| `analytics_service` | `rep_` | Эренедженова Мария | `L3_reporting_analyst.puml` | 7 |
| `etl_service` | `etl_` | Эренедженова Мария | `L3_etl_analyst.puml` | 6 |
| `monitoring` | `mon_` | Дамакальщиков Михаил | `L3_devops_monitoring.puml` | 7 |
| Итого | | | | 82 |

Файлы лежат в папках участников внутри `src/local/`.

### Компоненты (82)

Столбец «Слой / группа» показывает слой по локальной диаграмме. У `api_gateway`, `analytics_service`, `etl_service` и `monitoring` границы слоёв на диаграмме не нарисованы, поэтому группы выведены из назначения компонентов.

| Контейнер | Слой / группа | Локальный ID | Глобальный ID | Название компонента |
|---|---|---|---|---|
| `mobile_app` | Представление | `mob_ui_shell` | `mob_ui_shell` | UI-слой и навигация |
| `mobile_app` | Прикладная логика | `mob_catalog_controller` | `mob_catalog_controller` | Контроллер каталога и геопоиска |
| `mobile_app` | Прикладная логика | `mob_purchase_controller` | `mob_purchase_controller` | Контроллер покупки абонемента |
| `mobile_app` | Прикладная логика | `mob_pass_service` | `mob_pass_service` | Сервис электронного пропуска |
| `mobile_app` | Прикладная логика | `mob_session_service` | `mob_session_service` | Сервис сессии и авторизации |
| `mobile_app` | Доступ к данным и интеграции | `mob_api_client` | `mob_api_client` | Клиент API-шлюза |
| `mobile_app` | Доступ к данным и интеграции | `mob_secure_store` | `mob_secure_store` | Локальное защищённое хранилище |
| `mobile_app` | Доступ к данным и интеграции | `mob_payment_adapter` | `mob_payment_adapter` | Адаптер платёжного SDK |
| `mobile_app` | Доступ к данным и интеграции | `mob_push_handler` | `mob_push_handler` | Обработчик push-уведомлений |
| `admin_web` | Представление | `adm_ui_shell` | `adm_ui_shell` | Каркас SPA и навигация |
| `admin_web` | Прикладная логика | `adm_auth_service` | `adm_auth_service` | Сервис сессии и разграничения прав |
| `admin_web` | Прикладная логика | `adm_gym_profile_controller` | `adm_gym_profile_controller` | Контроллер карточки зала |
| `admin_web` | Прикладная логика | `adm_moderation_controller` | `adm_moderation_controller` | Контроллер модерации и обращений |
| `admin_web` | Прикладная логика | `adm_report_controller` | `adm_report_controller` | Контроллер отчётности |
| `admin_web` | Доступ к данным и интеграции | `adm_api_client` | `adm_api_client` | Клиент API-шлюза |
| `admin_web` | Доступ к данным и интеграции | `adm_file_service` | `adm_file_service` | Сервис файловых операций |
| `admin_web` | Доступ к данным и интеграции | `adm_state_store` | `adm_state_store` | Клиентское состояние и кэш |
| `api_gateway` | Входной контур | `tls_comp` | `gw_tls` | Модуль проверки TLS-сертификата |
| `api_gateway` | Входной контур | `ratelimit_comp` | `gw_ratelimit` | Модуль ограничения нагрузки |
| `api_gateway` | Контроль доступа | `authcheck_comp` | `gw_authcheck` | Модуль проверки доступа |
| `api_gateway` | Контроль доступа | `partner_comp` | `gw_partner` | Модуль доступа внешних систем |
| `api_gateway` | Маршрутизация | `router_comp` | `gw_router` | Модуль маршрутизации |
| `api_gateway` | Наблюдаемость | `metrics_comp` | `gw_metrics` | Модуль метрик |
| `auth_service` | API | `auth_api` | `auth_api` | API Аутентификации |
| `auth_service` | API | `oauth_api` | `auth_oauth_api` | API внешнего входа (SSO) |
| `auth_service` | API | `user_api` | `auth_user_api` | API Профилей |
| `auth_service` | Бизнес-логика | `auth_service_logic` | `auth_authn_service` | Сервис аутентификации |
| `auth_service` | Бизнес-логика | `oauth_service` | `auth_oauth_service` | Сервис OAuth 2.0 |
| `auth_service` | Бизнес-логика | `user_service` | `auth_user_service` | Сервис пользователей |
| `auth_service` | Бизнес-логика | `session_service` | `auth_session_service` | Сервис сессий |
| `auth_service` | Инфраструктура | `db_repository` | `auth_db_repository` | Репозиторий пользователей |
| `auth_service` | Инфраструктура | `cache_repository` | `auth_cache_repository` | Репозиторий сессий |
| `auth_service` | Инфраструктура | `idp_adapter` | `auth_idp_adapter` | Адаптер провайдера (IdP) |
| `core_api` | API | `catalog_api` | `core_catalog_api` | API Каталога и геопоиска |
| `core_api` | API | `booking_api` | `core_booking_api` | API Бронирования |
| `core_api` | API | `payment_api` | `core_payment_api` | API Оплат |
| `core_api` | API | `admin_tariff_api` | `core_admin_tariff_api` | API Управления тарифами |
| `core_api` | Бизнес-логика | `booking_service` | `core_booking_service` | Сервис бронирования |
| `core_api` | Бизнес-логика | `tariff_service` | `core_tariff_service` | Сервис тарификации |
| `core_api` | Бизнес-логика | `payment_service` | `core_payment_service` | Сервис оплат |
| `core_api` | Инфраструктура | `db_repository` | `core_db_repository` | Репозиторий БД |
| `core_api` | Инфраструктура | `iot_adapter` | `core_iot_adapter` | Адаптер СКУД |
| `core_api` | Инфраструктура | `integration_adapter` | `core_integration_adapter` | Адаптер интеграций |
| `integration_service` | API | `webhook_api_comp` | `int_webhook_api` | Контроллер webhook платёжной системы |
| `integration_service` | API | `integration_api_comp` | `int_internal_api` | Контроллер внутренних запросов |
| `integration_service` | Бизнес-логика | `payment_comp` | `int_payment_service` | Платёжный сервис |
| `integration_service` | Бизнес-логика | `payout_comp` | `int_payout_service` | Сервис выплат залам |
| `integration_service` | Бизнес-логика | `geocoding_comp` | `int_geocoding_service` | Сервис геокодирования |
| `integration_service` | Бизнес-логика | `notification_comp` | `int_notification_service` | Сервис уведомлений |
| `integration_service` | Инфраструктура | `acquiring_client_comp` | `int_acquiring_client` | Клиент платёжного шлюза |
| `integration_service` | Инфраструктура | `maps_client_comp` | `int_maps_client` | Клиент картографического сервиса |
| `integration_service` | Инфраструктура | `delivery_client_comp` | `int_delivery_client` | Клиент провайдеров доставки |
| `integration_service` | Инфраструктура | `integration_repo_comp` | `int_repository` | Репозиторий платежей и журнала обмена |
| `integration_service` | Инфраструктура | `integration_events_comp` | `int_event_bus` | Шина событий |
| `iot_service` | API | `iot_api_comp` | `iot_api` | Контроллер допуска и загруженности |
| `iot_service` | Бизнес-логика | `pass_comp` | `iot_pass_service` | Сервис QR-пропусков |
| `iot_service` | Бизнес-логика | `access_comp` | `iot_access_service` | Сервис допуска |
| `iot_service` | Бизнес-логика | `occupancy_comp` | `iot_occupancy_service` | Сервис индекса загруженности |
| `iot_service` | Инфраструктура | `mqtt_gateway_comp` | `iot_mqtt_client` | Клиент MQTT-брокера |
| `iot_service` | Инфраструктура | `iot_repo_comp` | `iot_repository` | Репозиторий событий прохода и истории загруженности |
| `iot_service` | Инфраструктура | `iot_cache_comp` | `iot_cache_client` | Клиент кэша |
| `iot_service` | Инфраструктура | `iot_events_comp` | `iot_event_bus` | Шина событий |
| `analytics_service` | API | `report_controller` | `rep_controller` | Контроллер отчётности |
| `analytics_service` | Бизнес-логика | `metrics_engine` | `rep_metrics_engine` | Модуль расчёта показателей |
| `analytics_service` | Бизнес-логика | `report_builder` | `rep_report_builder` | Сборщик отчётов |
| `analytics_service` | Бизнес-логика | `settlement_exporter` | `rep_settlement_exporter` | Модуль реестров начислений |
| `analytics_service` | Инфраструктура | `mart_repository` | `rep_mart_repository` | Репозиторий витрин |
| `analytics_service` | Инфраструктура | `storage_gateway` | `rep_storage_gateway` | Шлюз файлового хранилища |
| `analytics_service` | Инфраструктура | `event_publisher` | `rep_event_publisher` | Издатель событий |
| `etl_service` | Оркестрация | `dag_scheduler` | `etl_dag_scheduler` | Планировщик загрузок |
| `etl_service` | Извлечение | `db_extractor` | `etl_db_extractor` | Экстрактор операционных данных |
| `etl_service` | Извлечение | `event_consumer` | `etl_event_consumer` | Потребитель потока событий |
| `etl_service` | Преобразование и контроль качества | `transform_engine` | `etl_transform_engine` | Модуль преобразования |
| `etl_service` | Преобразование и контроль качества | `dq_validator` | `etl_dq_validator` | Модуль контроля качества данных |
| `etl_service` | Загрузка | `mart_loader` | `etl_mart_loader` | Загрузчик витрин |
| `monitoring` | Сбор | `scrape_comp` | `mon_scraper` | Сборщик метрик |
| `monitoring` | Хранение | `tsdb_comp` | `mon_tsdb` | Хранилище метрик |
| `monitoring` | Оповещения | `rules_comp` | `mon_rules` | Движок правил оповещений |
| `monitoring` | Оповещения | `alert_comp` | `mon_alerting` | Маршрутизатор оповещений |
| `monitoring` | Сбор | `log_agent` | `mon_log_agent` | Агент сбора логов |
| `monitoring` | Хранение | `logs_comp` | `mon_log_store` | Хранилище логов |
| `monitoring` | Визуализация | `viz_comp` | `mon_dashboards` | Панели визуализации |

### Стыковочные шлюзы контейнеров

Стыковочным шлюзом называется компонент, на который в локальной диаграмме приходит сетевая стрелка из другого контейнера, внешней системы или роли. На уровне 2 такая стрелка ведёт в контейнер как в чёрный ящик, на уровне 3 она уточняется до конкретного шлюза. Контейнеру разрешено иметь несколько шлюзов, если у входов разные инициаторы или разные предметные области.

| Контейнер | Шлюз | Протокол и порт | Кто обращается | Что передаётся |
|---|---|---|---|---|
| `mobile_app` | `mob_ui_shell` | GUI (Android / iOS) | `client` | Поиск зала, оформление абонемента, QR-пропуск |
| `mobile_app` | `mob_push_handler` | FCM / APNs | `notification_gateway` | Push-уведомления |
| `admin_web` | `adm_ui_shell` | HTTPS, GUI | `gym_admin`, `platform_operator`, `analyst` | Работа в панели |
| `api_gateway` | `gw_tls` | HTTPS/JSON, TCP 443 | `mobile_app`, `admin_web`, `payment_gateway`, `bi_platform` | Все внешние запросы, webhook, запросы BI |
| `api_gateway` | `gw_metrics` | HTTP GET /metrics | `monitoring` | Метрики Nginx |
| `auth_service` | `auth_api`, `auth_oauth_api`, `auth_user_api` | HTTP/JSON, TCP 8001 | `api_gateway` | Вход, обновление и проверка токенов, callback провайдера, профили |
| `core_api` | `core_catalog_api`, `core_booking_api`, `core_payment_api`, `core_admin_tariff_api` | HTTP/JSON, TCP 8000 | `api_gateway` | Каталог, покупка абонементов, оплата, тарифы |
| `integration_service` | `int_webhook_api` | HTTP/JSON, TCP 8002 | `api_gateway` | Webhook платёжного шлюза |
| `integration_service` | `int_internal_api` | HTTP/JSON, TCP 8002; HTTP GET /metrics | `core_api`, `monitoring` | Платёж, возврат, геокодирование; метрики |
| `iot_service` | `iot_api` | HTTP/JSON, TCP 8004 | `api_gateway`, `core_api` | QR-пропуски, ручные отметки, пересчёт индекса |
| `analytics_service` | `rep_controller` | HTTP/JSON, TCP 8003 | `api_gateway` | Показатели, отчёты, выгрузки |
| `etl_service` | нет | - | - | Загрузки запускает планировщик внутри контейнера |
| `monitoring` | `mon_dashboards` | HTTPS, TCP 3000 | `devops` | Панели и поиск по журналам |

### Связи между контейнерами

Сверка ведётся со стороны инициатора: берётся исходящая стрелка в диаграмме инициатора, затем в диаграмме приёмника ищется шлюз с тем же протоколом и портом.

| № | Инициатор | Приёмник | Шлюз приёмника | Протокол и порт |
|---|---|---|---|---|
| 1 | `mobile_app` (`mob_api_client`) | `api_gateway` | `gw_tls` | HTTPS/JSON, TCP 443 |
| 2 | `admin_web` (`adm_api_client`) | `api_gateway` | `gw_tls` | HTTPS/JSON, TCP 443 |
| 3 | `payment_gateway` | `api_gateway` | `gw_tls` | HTTPS/JSON, TCP 443 |
| 4 | `bi_platform` | `api_gateway` | `gw_tls` | SQL over HTTPS, TCP 443 |
| 5 | `monitoring` (`mon_scraper`) | `api_gateway` | `gw_metrics` | HTTP GET /metrics |
| 6 | `api_gateway` (`gw_authcheck`, `gw_router`) | `auth_service` | `auth_api`, `auth_oauth_api`, `auth_user_api` | HTTP/JSON, TCP 8001 |
| 7 | `api_gateway` (`gw_router`) | `core_api` | `core_catalog_api`, `core_booking_api`, `core_payment_api`, `core_admin_tariff_api` | HTTP/JSON, TCP 8000 |
| 8 | `api_gateway` (`gw_router`) | `analytics_service` | `rep_controller` | HTTP/JSON, TCP 8003 |
| 9 | `api_gateway` (`gw_router`) | `iot_service` | `iot_api` | HTTP/JSON, TCP 8004 |
| 10 | `api_gateway` (`gw_partner`) | `integration_service` | `int_webhook_api` | HTTP/JSON, TCP 8002 |
| 11 | `api_gateway` (`gw_partner`) | `dwh` | чёрный ящик | HTTP, TCP 8123 |
| 12 | `core_api` (`core_integration_adapter`) | `integration_service` | `int_internal_api` | HTTP/JSON, TCP 8002 |
| 13 | `core_api` (`core_iot_adapter`) | `iot_service` | `iot_api` | HTTP/JSON, TCP 8004 |
| 14 | `monitoring` (`mon_scraper`) | `integration_service` | `int_internal_api` | HTTP GET /metrics |
| 15 | `monitoring` (`mon_scraper`) | `database`, `message_broker` | чёрные ящики | HTTP GET /metrics, TCP 9187 и 15692 |

Опрос `/metrics` у `core_api`, `iot_service`, `auth_service` и `analytics_service` согласуется владельцами `monitoring` и соответствующих сервисов: сейчас `monitoring` опрашивает `core_api`, но в его диаграмме нет компонента, отдающего метрики, а `iot_api` отдаёт метрики, но не опрашивается.

Связи компонентов с хранилищами, брокерами и внешними системами (SQL 5432, RESP 6379, S3 9000, AMQP 5672, MQTT 1883, HTTP 8123, интеграции с внешними системами) идут только из компонентов инфраструктурного слоя и перечислены в отчёте по интеграции диаграмм уровня 3.

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
│   │       ├── lisov/
│   │       ├── kutenkov/
│   │       ├── Osipov_Ilya/
│   │       ├── erenmari/
│   │       └── damakalshchikov/
│   └── reports/                   # отчёт по курсовой работе
└── src/
    ├── main_context.puml          # исходник сводной диаграммы контекста
    ├── main_containers.puml       # исходник сводной диаграммы контейнеров
    ├── integrations/              # материалы интеграции локальных представлений
    └── local/                     # локальные диаграммы участников (контекст, контейнеры, компоненты)
        ├── lisov/
        ├── kutenkov/
        ├── Osipov_Ilya/
        ├── erenmari/
        └── damakalshchikov/
```

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

## Процесс работы

Каждый участник работает в своей ветке и вносит изменения в свою зону через Pull Request. Тимлид проводит ревью и оставляет комментарии до слияния в `main`. История коммитов отражает вклад каждого участника.
