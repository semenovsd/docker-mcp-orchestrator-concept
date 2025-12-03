# Docker MCP Orchestrator — Архитектурный документ

> **Версия:** 1.0  
> **Дата:** 3 декабря 2025  
> **Авторы:** Senior Agentic AI Engineer, Senior Solution Architect, Senior Python Developer  
> **Статус:** RFC (Request for Comments)

---

## 📋 Содержание

1. [Executive Summary](#1-executive-summary)
2. [Анализ проблемы](#2-анализ-проблемы)
3. [Ключевые архитектурные вызовы](#3-ключевые-архитектурные-вызовы)
4. [Исследование архитектурных подходов](#4-исследование-архитектурных-подходов)
5. [Рекомендуемая архитектура](#5-рекомендуемая-архитектура)
6. [Детальное описание компонентов](#6-детальное-описание-компонентов)
7. [Алгоритм определения нужных серверов](#7-алгоритм-определения-нужных-серверов)
8. [Альтернативные подходы](#8-альтернативные-подходы)
9. [Trade-offs и ограничения](#9-trade-offs-и-ограничения)
10. [Рекомендации по реализации](#10-рекомендации-по-реализации)
11. [Метрики успеха](#11-метрики-успеха)

---

## 1. Executive Summary

### Проблема
При работе с AI-помощниками (Cursor, Claude Desktop) подключение множества MCP серверов приводит к **перегрузке контекста** токенами от нерелевантных tools, что снижает качество ответов AI и приводит к превышению лимитов.

### Решение
**Docker MCP Orchestrator** — интеллектуальная прослойка между AI-клиентом и Docker MCP Toolkit, которая:
- Автоматически определяет минимально необходимый набор серверов для текущей задачи
- Динамически управляет жизненным циклом серверов
- Минимизирует количество tools в контексте AI

### Ключевая инновация
**Two-Phase Router Architecture** — разделение процесса на две фазы:
1. **Classification Phase** — легковесный анализ задачи через минимальный набор meta-tools
2. **Execution Phase** — работа с оптимальным набором активированных серверов

---

## 2. Анализ проблемы

### 2.1 Корневая причина

```
┌─────────────────────────────────────────────────────────────────┐
│                    Текущая ситуация                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   AI Client (Cursor)                                            │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │           MCP Connection                                │   │
│   │   ┌───────────────────────────────────────────────────┐ │   │
│   │   │  GitHub MCP      [50 tools] → 5000 tokens         │ │   │
│   │   │  PostgreSQL MCP  [30 tools] → 3000 tokens         │ │   │
│   │   │  FileSystem MCP  [20 tools] → 2000 tokens         │ │   │
│   │   │  Browser MCP     [40 tools] → 4000 tokens         │ │   │
│   │   │  Slack MCP       [25 tools] → 2500 tokens         │ │   │
│   │   │  ...10 more MCPs [200 tools] → 20000 tokens       │ │   │
│   │   └───────────────────────────────────────────────────┘ │   │
│   │                                                         │   │
│   │   TOTAL: ~365 tools = ~36,500 tokens в контексте       │   │
│   │   (До 30% контекстного окна занято descriptions tools!) │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   Результат: AI "тонет" в инструментах, качество падает        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Количественный анализ проблемы

| Метрика | Без оркестратора | С оркестратором (цель) |
|---------|------------------|------------------------|
| Среднее кол-во tools в контексте | 200-400 | 15-50 |
| Токены на описание tools | 20,000-40,000 | 1,500-5,000 |
| % контекстного окна на tools | 20-30% | 2-5% |
| Время выбора tool AI | 2-5 сек | 0.5-1 сек |
| Точность выбора tool | 70-80% | 95%+ |

### 2.3 Технические ограничения (Constraints)

| ID | Ограничение | Влияние на архитектуру |
|----|-------------|------------------------|
| **TC-1** | Cursor 2.x требует перезапуска соединения для обнаружения новых tools | Невозможно добавлять tools "на лету"; нужна стратегия минимизации reconnects |
| **TC-2** | MCP Protocol не поддерживает динамическое добавление tools | Подтверждает TC-1; требуется проектировать с учётом "cold start" |
| **TC-3** | Управление через CLI `docker mcp` | Асинхронные операции; необходим надёжный парсинг и очередь команд |
| **TC-4** | Token Budget критичен | Каждый лишний tool = потерянные токены для контента |

---

## 3. Ключевые архитектурные вызовы

### Challenge #1: Как определить нужные серверы ДО их активации?

**Парадокс курицы и яйца:**
- Чтобы понять, какие tools нужны, AI должен проанализировать задачу
- Чтобы AI мог анализировать, ему нужны tools в контексте
- Но мы хотим минимизировать tools в контексте

**Решение:** Двухфазная архитектура с **meta-level classification**

### Challenge #2: Как минимизировать количество reconnects?

**Проблема:** Каждый reconnect = задержка 3-5 секунд + прерывание workflow пользователя

**Решение:** Предиктивная загрузка + Session-based caching

### Challenge #3: Как обеспечить Zero-Configuration?

**Проблема:** Пользователь не должен думать о серверах

**Решение:** Semantic Server Registry + Intelligent Classification

---

## 4. Исследование архитектурных подходов

### 4.1 Подход A: Rule-Based Classification (Отвергнут)

```
User Query → Regex/Keyword Matching → Server Selection
```

**Плюсы:**
- Простота реализации
- Нулевая задержка
- Предсказуемость

**Минусы:**
- Не масштабируется на новые серверы
- Не понимает контекст и нюансы
- Высокий процент false positives/negatives
- Требует постоянного ручного обновления правил

**Вердикт:** ❌ Не подходит для enterprise-уровня

---

### 4.2 Подход B: LLM-based Classification (Рассмотрен)

```
User Query → Mini-LLM → Server List → Activation
```

**Плюсы:**
- Высокая точность понимания intent
- Адаптивность к новым серверам
- Понимание контекста

**Минусы:**
- Дополнительная задержка (1-3 сек на inference)
- Требует отдельного LLM или API-вызова
- Увеличивает стоимость (tokens)
- Single point of failure

**Вердикт:** ⚠️ Возможен как опциональный режим для сложных случаев

---

### 4.3 Подход C: Semantic Embedding Match (Рекомендован как компонент)

```
User Query → Embedding → Cosine Similarity → Top-K Servers
```

**Плюсы:**
- Быстрый inference (<100ms локально)
- Семантическое понимание
- Легко добавлять новые серверы
- Работает offline

**Минусы:**
- Требует качественных embeddings для серверов
- Может не уловить сложные зависимости
- Нужна периодическая переиндексация

**Вердикт:** ✅ Рекомендован как основной механизм

---

### 4.4 Подход D: Two-Phase Router (Рекомендован)

```
Phase 1: Orchestrator с 3-5 meta-tools → Classification
Phase 2: Активация нужных серверов → Reconnect → Execution
```

**Плюсы:**
- Минимальный initial footprint
- AI сам участвует в классификации
- Прозрачность решений
- Возможность уточнения

**Минусы:**
- Требует reconnect между фазами
- Сложнее в реализации

**Вердикт:** ✅ Рекомендован как основная архитектура

---

### 4.5 Подход E: Session Profiles (Рекомендован как дополнение)

```
User → Selects/Auto-detects Profile → Pre-configured Server Set
```

**Плюсы:**
- Мгновенная активация
- Предсказуемость
- Оптимизация под типовые сценарии

**Минусы:**
- Требует предварительной настройки
- Может не покрыть все сценарии

**Вердикт:** ✅ Рекомендован как дополнительный механизм

---

## 5. Рекомендуемая архитектура

### 5.1 Высокоуровневая архитектура

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOCKER MCP ORCHESTRATOR                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │  AI Client  │◄──►│              Orchestrator MCP Server             │   │
│  │  (Cursor)   │    │  ┌────────────────────────────────────────────┐  │   │
│  └─────────────┘    │  │           Meta-Tools Layer (3-5 tools)     │  │   │
│                     │  │  • analyze_task()                          │  │   │
│                     │  │  • list_available_capabilities()           │  │   │
│                     │  │  • activate_servers()                      │  │   │
│                     │  │  • get_active_tools()                      │  │   │
│                     │  │  • switch_context()                        │  │   │
│                     │  └────────────────────────────────────────────┘  │   │
│                     │                      │                           │   │
│                     │                      ▼                           │   │
│                     │  ┌────────────────────────────────────────────┐  │   │
│                     │  │         Classification Engine              │  │   │
│                     │  │  ┌──────────────────┐ ┌─────────────────┐  │  │   │
│                     │  │  │ Semantic Matcher │ │ Pattern Matcher │  │  │   │
│                     │  │  │   (Embeddings)   │ │  (Rule-based)   │  │  │   │
│                     │  │  └────────┬─────────┘ └────────┬────────┘  │  │   │
│                     │  │           └──────────┬─────────┘           │  │   │
│                     │  │                      ▼                     │  │   │
│                     │  │           ┌─────────────────┐              │  │   │
│                     │  │           │ Score Combiner  │              │  │   │
│                     │  │           └─────────────────┘              │  │   │
│                     │  └────────────────────────────────────────────┘  │   │
│                     │                      │                           │   │
│                     │                      ▼                           │   │
│                     │  ┌────────────────────────────────────────────┐  │   │
│                     │  │         Semantic Server Registry           │  │   │
│                     │  │  ┌─────────────────────────────────────┐   │  │   │
│                     │  │  │ Server Catalog (YAML/JSON)          │   │  │   │
│                     │  │  │ • name, description, capabilities   │   │  │   │
│                     │  │  │ • tool_categories, keywords         │   │  │   │
│                     │  │  │ • embedding vectors                 │   │  │   │
│                     │  │  │ • dependencies, conflicts           │   │  │   │
│                     │  │  └─────────────────────────────────────┘   │  │   │
│                     │  └────────────────────────────────────────────┘  │   │
│                     │                      │                           │   │
│                     └──────────────────────┼───────────────────────────┘   │
│                                            │                               │
│                                            ▼                               │
│                     ┌──────────────────────────────────────────────────┐   │
│                     │            Server Lifecycle Manager              │   │
│                     │  ┌─────────────────────────────────────────────┐ │   │
│                     │  │ • activate_server(name)                     │ │   │
│                     │  │ • deactivate_server(name)                   │ │   │
│                     │  │ • health_check()                            │ │   │
│                     │  │ • get_server_status()                       │ │   │
│                     │  └─────────────────────────────────────────────┘ │   │
│                     │                      │                           │   │
│                     │                      ▼                           │   │
│                     │  ┌─────────────────────────────────────────────┐ │   │
│                     │  │         Docker MCP Toolkit CLI              │ │   │
│                     │  │  docker mcp server enable/disable           │ │   │
│                     │  │  docker mcp gateway run --servers           │ │   │
│                     │  └─────────────────────────────────────────────┘ │   │
│                     └──────────────────────────────────────────────────┘   │
│                                            │                               │
│                                            ▼                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Docker MCP Gateway                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │  │
│  │  │ GitHub  │  │Postgres │  │  File   │  │ Browser │  │  Slack  │    │  │
│  │  │   MCP   │  │   MCP   │  │  System │  │   MCP   │  │   MCP   │    │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Архитектурный паттерн: Two-Phase Router

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TWO-PHASE ROUTER PATTERN                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ╔═══════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 1: CLASSIFICATION (Lightweight)                        ║  │
│  ╠═══════════════════════════════════════════════════════════════╣  │
│  ║                                                               ║  │
│  ║  User: "Мне нужно проанализировать PR #123 в репозитории     ║  │
│  ║         myorg/backend и проверить, не сломает ли он          ║  │
│  ║         миграции базы данных"                                 ║  │
│  ║                          │                                    ║  │
│  ║                          ▼                                    ║  │
│  ║  ┌─────────────────────────────────────────────────────────┐  ║  │
│  ║  │  Orchestrator Meta-Tools (в контексте AI):              │  ║  │
│  ║  │  • analyze_task() - 200 tokens                          │  ║  │
│  ║  │  • list_capabilities() - 150 tokens                     │  ║  │
│  ║  │  • activate_servers() - 100 tokens                      │  ║  │
│  ║  │  ─────────────────────────────────                      │  ║  │
│  ║  │  TOTAL: ~450 tokens (vs 36,500 без оркестратора)        │  ║  │
│  ║  └─────────────────────────────────────────────────────────┘  ║  │
│  ║                          │                                    ║  │
│  ║                          ▼                                    ║  │
│  ║  AI вызывает: analyze_task(task="analyze PR and DB impact")  ║  │
│  ║                          │                                    ║  │
│  ║                          ▼                                    ║  │
│  ║  Classification Engine возвращает:                            ║  │
│  ║  {                                                            ║  │
│  ║    "recommended_servers": ["github", "postgres"],             ║  │
│  ║    "confidence": 0.94,                                        ║  │
│  ║    "reasoning": "PR analysis requires GitHub MCP,             ║  │
│  ║                  DB migration check requires PostgreSQL MCP"  ║  │
│  ║  }                                                            ║  │
│  ║                          │                                    ║  │
│  ║                          ▼                                    ║  │
│  ║  AI вызывает: activate_servers(["github", "postgres"])       ║  │
│  ║                                                               ║  │
│  ╚═══════════════════════════════════════════════════════════════╝  │
│                          │                                          │
│                          │  ◄── RECONNECT (3-5 sec)                 │
│                          ▼                                          │
│  ╔═══════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 2: EXECUTION (Targeted)                                ║  │
│  ╠═══════════════════════════════════════════════════════════════╣  │
│  ║                                                               ║  │
│  ║  ┌─────────────────────────────────────────────────────────┐  ║  │
│  ║  │  Активные Tools (в контексте AI):                       │  ║  │
│  ║  │  • GitHub MCP: 12 tools - 1200 tokens                   │  ║  │
│  ║  │  • PostgreSQL MCP: 8 tools - 800 tokens                 │  ║  │
│  ║  │  • Orchestrator: 2 tools - 200 tokens (status, switch)  │  ║  │
│  ║  │  ─────────────────────────────────────                  │  ║  │
│  ║  │  TOTAL: 22 tools = ~2,200 tokens                        │  ║  │
│  ║  └─────────────────────────────────────────────────────────┘  ║  │
│  ║                          │                                    ║  │
│  ║                          ▼                                    ║  │
│  ║  AI выполняет задачу с релевантными tools                    ║  │
│  ║  • github.get_pull_request(#123)                             ║  │
│  ║  • github.get_diff()                                         ║  │
│  ║  • postgres.list_migrations()                                ║  │
│  ║  • postgres.analyze_schema_changes()                         ║  │
│  ║                                                               ║  │
│  ╚═══════════════════════════════════════════════════════════════╝  │
│                                                                     │
│  РЕЗУЛЬТАТ: 94% сокращение токенов на tools                        │
│             (2,200 vs 36,500)                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Компонентная диаграмма (C4 Level 2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Docker MCP Orchestrator                          │
│                         [Software System]                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MCP Server Interface                          │   │
│  │                    [Component: Python/FastMCP]                   │   │
│  │                                                                  │   │
│  │  Responsibilities:                                               │   │
│  │  • Expose MCP protocol endpoint                                  │   │
│  │  • Handle tool registration/deregistration                       │   │
│  │  • Manage client connections                                     │   │
│  │  • Coordinate reconnection signaling                             │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│          ┌──────────────────┼──────────────────┐                       │
│          │                  │                  │                        │
│          ▼                  ▼                  ▼                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │
│  │ Meta-Tools    │  │Classification │  │ Server        │               │
│  │ Registry      │  │ Engine        │  │ Lifecycle     │               │
│  │ [Component]   │  │ [Component]   │  │ Manager       │               │
│  │               │  │               │  │ [Component]   │               │
│  │ • analyze_    │  │ • Semantic    │  │               │               │
│  │   task()      │  │   Matcher     │  │ • activate()  │               │
│  │ • list_caps() │  │ • Pattern     │  │ • deactivate()│               │
│  │ • activate()  │  │   Matcher     │  │ • health()    │               │
│  │ • switch()    │  │ • Combiner    │  │ • status()    │               │
│  └───────────────┘  └───────┬───────┘  └───────┬───────┘               │
│                              │                  │                        │
│                              ▼                  │                        │
│                     ┌───────────────┐          │                        │
│                     │ Semantic      │          │                        │
│                     │ Server        │          │                        │
│                     │ Registry      │          │                        │
│                     │ [Component]   │          │                        │
│                     │               │          │                        │
│                     │ • Catalog     │          │                        │
│                     │ • Embeddings  │          │                        │
│                     │ • Metadata    │          │                        │
│                     └───────┬───────┘          │                        │
│                              │                  │                        │
│                              └────────┬─────────┘                       │
│                                       │                                  │
│                                       ▼                                  │
│                     ┌─────────────────────────────┐                     │
│                     │    Docker MCP CLI Adapter   │                     │
│                     │    [Component: Python]      │                     │
│                     │                             │                     │
│                     │  • Command executor         │                     │
│                     │  • Output parser            │                     │
│                     │  • Retry logic              │                     │
│                     │  • Command queue            │                     │
│                     └──────────────┬──────────────┘                     │
│                                    │                                     │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
                                     ▼
                     ┌─────────────────────────────┐
                     │   Docker MCP Toolkit        │
                     │   [External System]         │
                     │                             │
                     │   docker mcp gateway run    │
                     │   docker mcp server enable  │
                     │   docker mcp tools ls       │
                     └─────────────────────────────┘
```

---

## 6. Детальное описание компонентов

### 6.1 Meta-Tools Layer

**Назначение:** Предоставить AI минимальный набор инструментов для интеллектуального выбора нужных серверов.

#### Tool 1: `analyze_task`

```yaml
name: analyze_task
description: |
  Анализирует задачу пользователя и возвращает список рекомендуемых 
  MCP серверов с обоснованием. Вызывайте этот tool первым, 
  когда пользователь описывает новую задачу.

parameters:
  task_description:
    type: string
    description: Описание задачи пользователя
    required: true
  context_hints:
    type: array
    items: string
    description: Дополнительные подсказки о контексте (файлы, технологии)
    required: false

returns:
  recommended_servers:
    type: array
    description: Список рекомендуемых серверов в порядке релевантности
  confidence:
    type: number
    description: Уверенность классификации (0-1)
  reasoning:
    type: string
    description: Объяснение выбора серверов
  alternative_servers:
    type: array
    description: Альтернативные серверы, которые могут быть полезны

token_cost: ~200 tokens
```

#### Tool 2: `list_available_capabilities`

```yaml
name: list_available_capabilities
description: |
  Возвращает краткий список доступных категорий возможностей и 
  соответствующих им MCP серверов. Используйте для понимания, 
  какие типы задач может выполнять система.

parameters:
  category_filter:
    type: string
    description: Фильтр по категории (optional)
    enum: [databases, vcs, files, web, messaging, all]
    default: all

returns:
  capabilities:
    type: array
    items:
      category: string
      servers: array
      example_tasks: array

token_cost: ~150 tokens
```

#### Tool 3: `activate_servers`

```yaml
name: activate_servers
description: |
  Активирует указанные MCP серверы. После вызова потребуется 
  переподключение для доступа к tools этих серверов.
  
  ВАЖНО: После успешной активации клиент должен переподключиться 
  к MCP для получения новых tools.

parameters:
  servers:
    type: array
    items: string
    description: Список имён серверов для активации
    required: true
  deactivate_others:
    type: boolean
    description: Деактивировать неуказанные серверы
    default: true

returns:
  activated:
    type: array
    description: Успешно активированные серверы
  failed:
    type: array
    description: Серверы, которые не удалось активировать
  reconnect_required:
    type: boolean
    description: Требуется ли переподключение
  estimated_tools_count:
    type: integer
    description: Ожидаемое количество tools после переподключения

token_cost: ~100 tokens
```

#### Tool 4: `get_status`

```yaml
name: get_status
description: |
  Возвращает текущий статус оркестратора: активные серверы, 
  доступные tools, метрики производительности.

parameters: {}

returns:
  active_servers:
    type: array
  total_tools:
    type: integer
  session_id:
    type: string
  uptime:
    type: string

token_cost: ~80 tokens
```

#### Tool 5: `switch_context`

```yaml
name: switch_context
description: |
  Быстрое переключение на предустановленный профиль серверов 
  или запрос дополнительных серверов к текущему набору.

parameters:
  profile:
    type: string
    description: Имя профиля (web-dev, data-eng, devops, etc.)
    required: false
  add_servers:
    type: array
    description: Дополнительные серверы к текущим
    required: false
  remove_servers:
    type: array
    description: Серверы для деактивации
    required: false

returns:
  new_configuration:
    type: object
  reconnect_required:
    type: boolean

token_cost: ~100 tokens
```

**Общий footprint Meta-Tools: ~630 tokens** (vs 36,500 для всех серверов)

---

### 6.2 Semantic Server Registry

**Назначение:** Хранение структурированной информации о серверах для интеллектуальной классификации.

#### Структура записи сервера

```yaml
# ~/.docker/mcp-orchestrator/registry/servers/github.yaml

server:
  name: github
  display_name: "GitHub MCP Server"
  docker_image: "mcp/github:latest"
  
  # Семантическое описание для классификации
  semantic:
    description: |
      GitHub integration for repository management, pull requests, 
      issues, code review, and GitHub Actions workflows.
    
    # Ключевые слова для pattern matching
    keywords:
      - github
      - repository
      - pull request
      - PR
      - issue
      - commit
      - branch
      - merge
      - git
      - code review
      - actions
      - workflow
      - CI/CD
    
    # Категории возможностей
    capabilities:
      - version_control
      - code_review
      - project_management
      - ci_cd
    
    # Типичные задачи (для embeddings)
    example_tasks:
      - "Review pull request"
      - "Create new branch"
      - "Analyze commit history"
      - "Check CI/CD status"
      - "Manage GitHub issues"
      - "Merge branches"
    
    # Pre-computed embedding vector (384 dimensions для all-MiniLM-L6-v2)
    embedding_vector: [0.023, -0.145, 0.089, ...]
  
  # Информация о tools
  tools:
    count: 45
    categories:
      repository: 12
      pull_requests: 15
      issues: 10
      actions: 8
    
    # Ключевые tools (для отображения пользователю)
    highlights:
      - get_pull_request
      - create_issue
      - list_commits
      - trigger_workflow
  
  # Зависимости и конфликты
  relations:
    requires: []  # Серверы, которые должны быть активны вместе
    recommends:   # Серверы, которые часто используются вместе
      - filesystem
    conflicts: [] # Серверы, которые не должны быть активны одновременно
  
  # Метаданные для управления
  metadata:
    token_cost_estimate: 4500  # Примерная стоимость в токенах
    startup_time_ms: 2000
    memory_mb: 256
    requires_secrets:
      - GITHUB_TOKEN
```

#### Индексация и поиск

```yaml
# ~/.docker/mcp-orchestrator/registry/index.yaml

index:
  version: 2
  last_updated: "2025-12-03T10:00:00Z"
  
  # Категории для быстрой фильтрации
  categories:
    databases:
      - postgres
      - mysql
      - mongodb
      - redis
    version_control:
      - github
      - gitlab
      - bitbucket
    files:
      - filesystem
      - s3
      - gcs
    web:
      - browser
      - puppeteer
      - playwright
    messaging:
      - slack
      - discord
      - teams
  
  # Профили для быстрого переключения
  profiles:
    web-development:
      servers: [github, filesystem, browser, postgres]
      description: "Full-stack web development"
    
    data-engineering:
      servers: [postgres, mongodb, s3, filesystem]
      description: "Data pipelines and ETL"
    
    devops:
      servers: [github, kubernetes, terraform, aws]
      description: "Infrastructure and deployments"
  
  # Embedding модель
  embedding:
    model: "all-MiniLM-L6-v2"
    dimensions: 384
    similarity_threshold: 0.65
```

---

### 6.3 Classification Engine

**Назначение:** Определение оптимального набора серверов на основе анализа задачи.

#### Алгоритм классификации (Hybrid Approach)

```
┌─────────────────────────────────────────────────────────────────┐
│              CLASSIFICATION ENGINE PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input: task_description + context_hints                        │
│         "Analyze PR #123 and check DB migration impact"         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ STAGE 1: Preprocessing                                    │  │
│  │ • Tokenization                                            │  │
│  │ • Named Entity Recognition (optional)                     │  │
│  │ • Keyword Extraction                                      │  │
│  │                                                           │  │
│  │ Output: ["PR", "analyze", "DB", "migration", "#123"]      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ STAGE 2: Pattern Matching (Fast Path)                     │  │
│  │ • Exact keyword match against server keywords             │  │
│  │ • Regex patterns for common intents                       │  │
│  │                                                           │  │
│  │ Matches:                                                  │  │
│  │ • "PR" → github (confidence: 0.9)                         │  │
│  │ • "DB", "migration" → postgres (confidence: 0.8)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ STAGE 3: Semantic Matching (Deep Path)                    │  │
│  │ • Generate embedding for task description                 │  │
│  │ • Cosine similarity with all server embeddings            │  │
│  │ • Top-K selection                                         │  │
│  │                                                           │  │
│  │ Similarities:                                             │  │
│  │ • github: 0.87                                            │  │
│  │ • postgres: 0.82                                          │  │
│  │ • filesystem: 0.45                                        │  │
│  │ • slack: 0.12                                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ STAGE 4: Score Combination                                │  │
│  │ • Weighted average of pattern + semantic scores           │  │
│  │ • Apply dependency resolution                             │  │
│  │ • Apply conflict checking                                 │  │
│  │                                                           │  │
│  │ Formula:                                                  │  │
│  │ final_score = α * pattern_score + (1-α) * semantic_score  │  │
│  │ where α = 0.4 (tunable)                                   │  │
│  │                                                           │  │
│  │ Final Scores:                                             │  │
│  │ • github: 0.4 * 0.9 + 0.6 * 0.87 = 0.882                  │  │
│  │ • postgres: 0.4 * 0.8 + 0.6 * 0.82 = 0.812                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ STAGE 5: Threshold & Selection                            │  │
│  │ • Select servers with score > threshold (0.6)             │  │
│  │ • Apply max_servers limit (default: 5)                    │  │
│  │ • Add required dependencies                               │  │
│  │                                                           │  │
│  │ Output:                                                   │  │
│  │ {                                                         │  │
│  │   "recommended_servers": ["github", "postgres"],          │  │
│  │   "confidence": 0.847,                                    │  │
│  │   "reasoning": "Task involves PR analysis (github) and    │  │
│  │                 database migration checking (postgres)"   │  │
│  │ }                                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6.4 Server Lifecycle Manager

**Назначение:** Управление жизненным циклом MCP серверов через Docker MCP Toolkit.

#### State Machine для сервера

```
                    ┌─────────────┐
                    │   Unknown   │
                    └──────┬──────┘
                           │ discover()
                           ▼
                    ┌─────────────┐
         ┌─────────│   Inactive  │◄────────────┐
         │         └──────┬──────┘             │
         │                │ activate()         │ deactivate()
         │                ▼                    │
         │         ┌─────────────┐             │
         │         │  Starting   │             │
         │         └──────┬──────┘             │
         │                │ ready              │
         │                ▼                    │
         │         ┌─────────────┐             │
         │         │   Active    │─────────────┤
         │         └──────┬──────┘             │
         │                │ error              │
         │                ▼                    │
         │         ┌─────────────┐             │
         └─────────│   Error     │─────────────┘
                   └─────────────┘
                         │ recover()
                         ▼
                   ┌─────────────┐
                   │  Recovering │
                   └─────────────┘
```

#### Command Queue Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COMMAND QUEUE                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Priority Queue                                       │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ P0 (Critical): Health checks, Emergency stops   │ │   │
│  │ ├─────────────────────────────────────────────────┤ │   │
│  │ │ P1 (High): Activate/Deactivate requests         │ │   │
│  │ ├─────────────────────────────────────────────────┤ │   │
│  │ │ P2 (Normal): Status queries, List operations    │ │   │
│  │ ├─────────────────────────────────────────────────┤ │   │
│  │ │ P3 (Low): Cleanup, Optimization tasks           │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Command Executor                                     │   │
│  │ • Concurrent execution (configurable workers)        │   │
│  │ • Retry with exponential backoff                     │   │
│  │ • Timeout handling                                   │   │
│  │ • Result caching                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Docker MCP CLI Adapter                               │   │
│  │ • Command builder                                    │   │
│  │ • JSON output parser                                 │   │
│  │ • Error classification                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Алгоритм определения нужных серверов

### 7.1 Основной алгоритм (Flowchart)

```
┌─────────────────────────────────────────────────────────────────────┐
│            АЛГОРИТМ ОПРЕДЕЛЕНИЯ НУЖНЫХ СЕРВЕРОВ                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  START                                                              │
│    │                                                                │
│    ▼                                                                │
│  ┌─────────────────────────────────────┐                           │
│  │ 1. Получить task_description от AI  │                           │
│  │    через analyze_task() tool        │                           │
│  └──────────────────┬──────────────────┘                           │
│                     │                                               │
│                     ▼                                               │
│  ┌─────────────────────────────────────┐                           │
│  │ 2. Проверить кэш сессии:            │                           │
│  │    Есть ли похожая задача?          │                           │
│  └──────────────────┬──────────────────┘                           │
│                     │                                               │
│           ┌────────┴────────┐                                      │
│           │                 │                                       │
│         [ДА]              [НЕТ]                                     │
│           │                 │                                       │
│           ▼                 ▼                                       │
│  ┌─────────────────┐  ┌─────────────────────────────────────┐      │
│  │ Вернуть        │  │ 3. Извлечь ключевые слова и          │      │
│  │ кэшированный   │  │    сущности из описания              │      │
│  │ результат      │  └──────────────────┬──────────────────┘      │
│  └────────┬────────┘                    │                          │
│           │                             ▼                          │
│           │            ┌─────────────────────────────────────┐     │
│           │            │ 4. Pattern Matching:                │     │
│           │            │    Сопоставить keywords с серверами │     │
│           │            └──────────────────┬──────────────────┘     │
│           │                               │                        │
│           │                               ▼                        │
│           │            ┌─────────────────────────────────────┐     │
│           │            │ 5. Semantic Matching:               │     │
│           │            │    Вычислить embedding задачи       │     │
│           │            │    Найти Top-K похожих серверов     │     │
│           │            └──────────────────┬──────────────────┘     │
│           │                               │                        │
│           │                               ▼                        │
│           │            ┌─────────────────────────────────────┐     │
│           │            │ 6. Объединить scores:               │     │
│           │            │    final = α*pattern + (1-α)*semantic│    │
│           │            └──────────────────┬──────────────────┘     │
│           │                               │                        │
│           │                               ▼                        │
│           │            ┌─────────────────────────────────────┐     │
│           │            │ 7. Отфильтровать по порогу:         │     │
│           │            │    score > 0.6                      │     │
│           │            └──────────────────┬──────────────────┘     │
│           │                               │                        │
│           │                               ▼                        │
│           │            ┌─────────────────────────────────────┐     │
│           │            │ 8. Применить ограничения:           │     │
│           │            │    • max_servers ≤ 5                │     │
│           │            │    • max_tools ≤ 100                │     │
│           │            │    • max_tokens ≤ 10000             │     │
│           │            └──────────────────┬──────────────────┘     │
│           │                               │                        │
│           │                               ▼                        │
│           │            ┌─────────────────────────────────────┐     │
│           │            │ 9. Разрешить зависимости:           │     │
│           │            │    Добавить required серверы        │     │
│           │            │    Проверить conflicts              │     │
│           │            └──────────────────┬──────────────────┘     │
│           │                               │                        │
│           │                               ▼                        │
│           │            ┌─────────────────────────────────────┐     │
│           │            │ 10. Сохранить в кэш сессии          │     │
│           │            └──────────────────┬──────────────────┘     │
│           │                               │                        │
│           └───────────────────────────────┘                        │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 11. Вернуть результат:                                      │   │
│  │     {                                                       │   │
│  │       recommended_servers: ["github", "postgres"],          │   │
│  │       confidence: 0.847,                                    │   │
│  │       reasoning: "...",                                     │   │
│  │       estimated_tools: 53,                                  │   │
│  │       estimated_tokens: 5300                                │   │
│  │     }                                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│                             END                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Стратегии оптимизации выбора

#### Стратегия 1: Greedy Selection with Budget

```python
# Псевдокод алгоритма жадного выбора с бюджетом
def select_servers_with_budget(candidates, token_budget=10000):
    selected = []
    current_tokens = 0
    
    # Сортируем по score / token_cost (efficiency)
    sorted_candidates = sort_by(candidates, key=score/token_cost, desc=True)
    
    for server in sorted_candidates:
        if current_tokens + server.token_cost <= token_budget:
            selected.append(server)
            current_tokens += server.token_cost
        
        if len(selected) >= MAX_SERVERS:
            break
    
    return selected
```

#### Стратегия 2: Dependency-Aware Selection

```python
# Псевдокод выбора с учётом зависимостей
def select_with_dependencies(primary_servers, registry):
    result = set(primary_servers)
    
    for server in primary_servers:
        # Добавляем обязательные зависимости
        result.update(registry[server].requires)
        
        # Проверяем конфликты
        for conflict in registry[server].conflicts:
            if conflict in result:
                # Разрешаем конфликт: оставляем сервер с большим score
                result.discard(lower_score(server, conflict))
    
    return result
```

#### Стратегия 3: Context-Aware Enhancement

```python
# Псевдокод контекстного улучшения
def enhance_with_context(servers, user_context):
    enhanced = servers.copy()
    
    # Анализируем файлы в текущей директории
    if has_python_files(user_context.cwd):
        boost_score("python-tools", +0.2)
    
    # Анализируем git remote
    if github_remote_detected(user_context.git):
        boost_score("github", +0.3)
    
    # Анализируем docker-compose
    if has_docker_compose(user_context.cwd):
        services = parse_docker_compose()
        for service in services:
            boost_score(map_service_to_mcp(service), +0.2)
    
    return re_rank(enhanced)
```

---

## 8. Альтернативные подходы

### 8.1 Подход A: LLM-in-the-Loop Classification

**Описание:** Использование отдельного LLM-вызова для классификации задачи.

```
┌─────────────────────────────────────────────────────────────────┐
│                 LLM-IN-THE-LOOP ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Query                                                     │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Classification LLM (GPT-4o-mini / Claude Haiku)         │   │
│  │                                                         │   │
│  │ System Prompt:                                          │   │
│  │ "Given the following task and list of available MCP     │   │
│  │  servers, return JSON with recommended servers..."      │   │
│  │                                                         │   │
│  │ Input: task + server_catalog                            │   │
│  │ Output: {servers: [...], reasoning: "..."}              │   │
│  └─────────────────────────────────────────────────────────┘   │
│      │                                                          │
│      ▼                                                          │
│  Server Activation → Reconnect → Main AI Session               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Преимущества:**
- Высокая точность понимания intent
- Способность к reasoning о сложных зависимостях
- Адаптивность к новым сценариям

**Недостатки:**
- Дополнительная задержка (1-3 сек)
- Дополнительные costs (tokens)
- Зависимость от внешнего API
- Single point of failure

**Рекомендация:** Использовать как **fallback** при низкой confidence основного алгоритма.

---

### 8.2 Подход B: User-Assisted Classification

**Описание:** Пользователь явно указывает контекст или профиль работы.

```
┌─────────────────────────────────────────────────────────────────┐
│                USER-ASSISTED CLASSIFICATION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Option 1: Profile Selection (UI/CLI)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ $ docker mcp orchestrator --profile=web-development      │   │
│  │                                                         │   │
│  │ Profiles:                                               │   │
│  │ [1] web-development  - GitHub, Postgres, Filesystem     │   │
│  │ [2] data-engineering - Postgres, MongoDB, S3            │   │
│  │ [3] devops           - GitHub, K8s, Terraform           │   │
│  │ [4] custom           - Interactive selection            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Option 2: Project-Based Detection                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ # .mcp-orchestrator.yaml в корне проекта                │   │
│  │                                                         │   │
│  │ servers:                                                │   │
│  │   required:                                             │   │
│  │     - github                                            │   │
│  │     - postgres                                          │   │
│  │   optional:                                             │   │
│  │     - redis                                             │   │
│  │     - elasticsearch                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Option 3: Natural Language Hint                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ User: "@orchestrator I'm working on backend development │   │
│  │        with PostgreSQL and will need GitHub for PRs"    │   │
│  │                                                         │   │
│  │ System: Activating: github, postgres, filesystem        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Преимущества:**
- Мгновенная активация (нет inference)
- 100% точность (пользователь знает лучше)
- Простота реализации

**Недостатки:**
- Нарушает принцип Zero-Configuration
- Требует обучения пользователя
- Может быть неудобно для ad-hoc задач

**Рекомендация:** Использовать как **дополнительный механизм** для power users.

---

### 8.3 Подход C: Lazy Loading with Progressive Enhancement

**Описание:** Начинаем с минимума, добавляем по мере необходимости.

```
┌─────────────────────────────────────────────────────────────────┐
│               LAZY LOADING ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Time ─────────────────────────────────────────────────────►    │
│                                                                 │
│  T0: Initial Session                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Active: Orchestrator only (5 meta-tools)                │   │
│  │ Tokens: ~500                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                     │                                          │
│                     │ User: "Check my GitHub PR"               │
│                     │ AI: calls analyze_task()                 │
│                     │ AI: calls activate_servers(["github"])   │
│                     ▼                                          │
│  T1: After First Activation (reconnect)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Active: Orchestrator + GitHub                           │   │
│  │ Tokens: ~500 + ~4500 = ~5000                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                     │                                          │
│                     │ User: "Now check the database schema"    │
│                     │ AI: calls activate_servers(["postgres"]) │
│                     ▼                                          │
│  T2: After Second Activation (reconnect)                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Active: Orchestrator + GitHub + Postgres                │   │
│  │ Tokens: ~500 + ~4500 + ~3000 = ~8000                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Преимущества:**
- Минимальный начальный footprint
- Естественный UX (AI решает сам)
- Не нужно предсказывать заранее

**Недостатки:**
- Множественные reconnects (плохой UX)
- Задержки при каждом добавлении
- Сложность управления состоянием

**Рекомендация:** Использовать как **fallback** когда основной алгоритм имеет низкую confidence.

---

### 8.4 Сравнительная таблица подходов

| Критерий | Semantic+Pattern (Основной) | LLM-in-Loop | User-Assisted | Lazy Loading |
|----------|----------------------------|-------------|---------------|--------------|
| **Точность** | 85-90% | 95%+ | 100% | 100% |
| **Задержка** | <100ms | 1-3s | 0ms | 3-5s/reconnect |
| **Cost** | Бесплатно | $$$ | Бесплатно | Бесплатно |
| **Zero-Config** | ✅ | ✅ | ❌ | ✅ |
| **Масштабируемость** | Отличная | Хорошая | Средняя | Плохая |
| **Complexity** | Средняя | Высокая | Низкая | Высокая |

**Рекомендуемая комбинация:**
1. **Primary:** Semantic + Pattern Matching
2. **Fallback при low confidence:** LLM-in-Loop
3. **Override для power users:** User-Assisted (profiles)
4. **Динамическое расширение:** Lazy Loading (для edge cases)

---

## 9. Trade-offs и ограничения

### 9.1 Trade-off Matrix

| Trade-off | Выбор | Обоснование |
|-----------|-------|-------------|
| **Точность vs Скорость** | Баланс (85% accuracy, <100ms) | Для enterprise важны оба |
| **Автоматизация vs Контроль** | Автоматизация с override | Zero-config важнее для большинства |
| **Простота vs Гибкость** | Гибкость | Enterprise требует кастомизации |
| **Local vs Cloud** | Local-first | Приватность, offline, скорость |

### 9.2 Известные ограничения

#### Ограничение 1: Reconnect Latency
**Проблема:** Каждое изменение набора серверов требует reconnect (3-5 сек).

**Митигация:**
- Предиктивная загрузка вероятных серверов
- Session-based caching
- Оптимизация startup времени серверов

#### Ограничение 2: Cold Start
**Проблема:** При первом запуске нет истории для предсказаний.

**Митигация:**
- Дефолтные профили по типу проекта
- Быстрое обучение на первых запросах
- Опциональный onboarding wizard

#### Ограничение 3: Multi-Domain Tasks
**Проблема:** Задача охватывает много доменов (>5 серверов).

**Митигация:**
- Tool-level filtering (не все tools с сервера)
- Поэтапное выполнение
- Приоритизация по relevance

#### Ограничение 4: Embedding Quality
**Проблема:** Качество embeddings зависит от описаний серверов.

**Митигация:**
- Ручная курация описаний для популярных серверов
- A/B тестирование разных моделей embeddings
- Feedback loop от пользователей

---

## 10. Рекомендации по реализации

### 10.1 Фазы реализации

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROADMAP РЕАЛИЗАЦИИ                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 1: MVP (2-3 недели)                                      │
│  ─────────────────────────                                      │
│  • MCP Server с 3 meta-tools (analyze, activate, status)        │
│  • Pattern Matching классификатор                               │
│  • Базовый Server Registry (YAML)                               │
│  • Docker MCP CLI integration                                   │
│  • Тестирование с Cursor                                        │
│                                                                 │
│  PHASE 2: Semantic Enhancement (2-3 недели)                     │
│  ─────────────────────────────────────────                      │
│  • Интеграция sentence-transformers                             │
│  • Pre-computed embeddings для серверов                         │
│  • Hybrid scoring (pattern + semantic)                          │
│  • Session caching                                              │
│  • Metrics & logging                                            │
│                                                                 │
│  PHASE 3: Intelligence (2-4 недели)                             │
│  ───────────────────────────────────                            │
│  • LLM fallback для low-confidence                              │
│  • Learning from usage patterns                                 │
│  • Auto-profile detection                                       │
│  • Performance optimization                                     │
│                                                                 │
│  PHASE 4: Enterprise Features (3-4 недели)                      │
│  ─────────────────────────────────────────                      │
│  • Multi-tenant support                                         │
│  • Admin dashboard                                              │
│  • Custom server catalog                                        │
│  • Compliance & audit logging                                   │
│  • High availability                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Технологический стек (рекомендуемый)

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| MCP Server | Python + FastMCP | Простота, ecosystem |
| Embedding Model | all-MiniLM-L6-v2 | Баланс качество/скорость |
| Server Registry | YAML + SQLite | Простота + persistence |
| CLI Integration | subprocess + asyncio | Надёжность |
| Caching | diskcache / Redis | Persistence |
| Metrics | Prometheus + Grafana | Industry standard |
| Testing | pytest + httpx | Python ecosystem |

### 10.3 Ключевые метрики для отслеживания

```yaml
metrics:
  # Accuracy
  classification_accuracy:
    description: "% правильно выбранных серверов"
    target: ">90%"
    
  false_positive_rate:
    description: "% ненужных серверов в выборке"
    target: "<10%"
    
  false_negative_rate:
    description: "% пропущенных нужных серверов"
    target: "<5%"
  
  # Performance
  classification_latency_p50:
    description: "Медиана времени классификации"
    target: "<50ms"
    
  classification_latency_p99:
    description: "99-й перцентиль времени классификации"
    target: "<200ms"
    
  activation_latency:
    description: "Время активации серверов"
    target: "<3s"
  
  # Token Efficiency
  context_reduction_ratio:
    description: "Сокращение токенов vs all-servers"
    target: ">80%"
    
  avg_tools_in_context:
    description: "Среднее количество tools"
    target: "<50"
  
  # User Experience
  reconnects_per_session:
    description: "Количество переподключений за сессию"
    target: "<2"
    
  user_override_rate:
    description: "% сессий с ручным override"
    target: "<10%"
```

---

## 11. Метрики успеха

### 11.1 KPIs для оценки решения

| KPI | Baseline (без оркестратора) | Target (с оркестратором) | Измерение |
|-----|----------------------------|--------------------------|-----------|
| Tools в контексте | 200-400 | 15-50 | Среднее за сессию |
| Токены на tools | 20,000-40,000 | 1,500-5,000 | Среднее за запрос |
| Время выбора tool AI | 2-5 сек | 0.5-1 сек | P50 latency |
| Точность выбора tool | 70-80% | 95%+ | A/B test |
| User satisfaction | Baseline | +30% | NPS survey |

### 11.2 Success Criteria для MVP

1. ✅ Оркестратор успешно подключается к Cursor как MCP server
2. ✅ Классификация задач работает с accuracy >80%
3. ✅ Активация/деактивация серверов через Docker MCP CLI
4. ✅ Сокращение tools в контексте на >70%
5. ✅ Время классификации <200ms (P99)
6. ✅ Документация и примеры использования

---

## 12. Заключение

### Ключевые решения архитектуры:

1. **Two-Phase Router Pattern** — разделение на фазу классификации (минимальные meta-tools) и фазу выполнения (целевые серверы)

2. **Hybrid Classification Engine** — комбинация Pattern Matching (быстрый, точный для известных паттернов) и Semantic Matching (гибкий, понимает контекст)

3. **Semantic Server Registry** — структурированный каталог с embeddings для интеллектуального выбора

4. **Graceful Degradation** — многоуровневые fallbacks (semantic → LLM → user input)

5. **Local-First Processing** — минимизация зависимости от внешних API для скорости и приватности

### Главное архитектурное преимущество:

> **Оркестратор превращает проблему "N серверов × M tools = O(N×M) токенов" в "K релевантных tools = O(K) токенов", где K << N×M**

Это достигается за счёт **интеллектуальной pre-flight классификации**, которая анализирует задачу ДО загрузки tools в контекст AI.

---

## 13. Sequence Diagrams

### 13.1 Основной Flow: Two-Phase Router

```
┌─────────┐     ┌─────────────┐     ┌────────────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │     │  AI Client  │     │  Orchestrator  │     │ ClassEngine │     │ Docker MCP  │
│         │     │  (Cursor)   │     │   MCP Server   │     │             │     │   Toolkit   │
└────┬────┘     └──────┬──────┘     └───────┬────────┘     └──────┬──────┘     └──────┬──────┘
     │                 │                    │                     │                   │
     │ "Проверь PR     │                    │                     │                   │
     │  и миграции БД" │                    │                     │                   │
     │────────────────>│                    │                     │                   │
     │                 │                    │                     │                   │
     │                 │ ╔═══════════════════════════════════════════════════════════════╗
     │                 │ ║ PHASE 1: CLASSIFICATION                                      ║
     │                 │ ╚═══════════════════════════════════════════════════════════════╝
     │                 │                    │                     │                   │
     │                 │  analyze_task()    │                     │                   │
     │                 │───────────────────>│                     │                   │
     │                 │                    │                     │                   │
     │                 │                    │  classify(task)     │                   │
     │                 │                    │────────────────────>│                   │
     │                 │                    │                     │                   │
     │                 │                    │                     │ ┌───────────────┐ │
     │                 │                    │                     │ │Pattern Match  │ │
     │                 │                    │                     │ │+ Semantic     │ │
     │                 │                    │                     │ │  Similarity   │ │
     │                 │                    │                     │ └───────────────┘ │
     │                 │                    │                     │                   │
     │                 │                    │  {github, postgres} │                   │
     │                 │                    │<────────────────────│                   │
     │                 │                    │                     │                   │
     │                 │  {recommended:     │                     │                   │
     │                 │   [github,postgres]│                     │                   │
     │                 │   confidence: 0.94}│                     │                   │
     │                 │<───────────────────│                     │                   │
     │                 │                    │                     │                   │
     │                 │ activate_servers() │                     │                   │
     │                 │───────────────────>│                     │                   │
     │                 │                    │                     │                   │
     │                 │                    │  docker mcp server enable github        │
     │                 │                    │─────────────────────────────────────────>│
     │                 │                    │                     │                   │
     │                 │                    │  docker mcp server enable postgres      │
     │                 │                    │─────────────────────────────────────────>│
     │                 │                    │                     │                   │
     │                 │                    │                OK   │                   │
     │                 │                    │<─────────────────────────────────────────│
     │                 │                    │                     │                   │
     │                 │  {activated: true, │                     │                   │
     │                 │   reconnect: true} │                     │                   │
     │                 │<───────────────────│                     │                   │
     │                 │                    │                     │                   │
     │                 │ ╔═══════════════════════════════════════════════════════════════╗
     │                 │ ║ RECONNECT (MCP Protocol requirement)                         ║
     │                 │ ╚═══════════════════════════════════════════════════════════════╝
     │                 │                    │                     │                   │
     │                 │  [Reconnect to     │                     │                   │
     │                 │   get new tools]   │                     │                   │
     │                 │═══════════════════>│                     │                   │
     │                 │                    │                     │                   │
     │                 │  tools: [github.*, │                     │                   │
     │                 │   postgres.*, orch]│                     │                   │
     │                 │<═══════════════════│                     │                   │
     │                 │                    │                     │                   │
     │                 │ ╔═══════════════════════════════════════════════════════════════╗
     │                 │ ║ PHASE 2: EXECUTION (with targeted tools)                     ║
     │                 │ ╚═══════════════════════════════════════════════════════════════╝
     │                 │                    │                     │                   │
     │                 │ github.get_pr(123) │                     │                   │
     │                 │───────────────────>│                     │                   │
     │                 │                    │                     │       GitHub      │
     │                 │                    │─────────────────────────────────────────>│
     │                 │  {pr_data}         │                     │                   │
     │                 │<───────────────────│                     │                   │
     │                 │                    │                     │                   │
     │                 │ postgres.          │                     │                   │
     │                 │  list_migrations() │                     │                   │
     │                 │───────────────────>│                     │                   │
     │                 │                    │                     │      Postgres     │
     │                 │                    │─────────────────────────────────────────>│
     │                 │  {migrations}      │                     │                   │
     │                 │<───────────────────│                     │                   │
     │                 │                    │                     │                   │
     │  "PR #123 не    │                    │                     │                   │
     │   затрагивает   │                    │                     │                   │
     │   миграции БД"  │                    │                     │                   │
     │<────────────────│                    │                     │                   │
     │                 │                    │                     │                   │
     ▼                 ▼                    ▼                     ▼                   ▼
```

### 13.2 Fallback Flow: LLM-Assisted Classification

```
┌─────────┐     ┌─────────────┐     ┌────────────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │     │  AI Client  │     │  Orchestrator  │     │ ClassEngine │     │  LLM API    │
└────┬────┘     └──────┬──────┘     └───────┬────────┘     └──────┬──────┘     └──────┬──────┘
     │                 │                    │                     │                   │
     │ "Сложная        │                    │                     │                   │
     │  неоднозначная  │                    │                     │                   │
     │  задача..."     │                    │                     │                   │
     │────────────────>│                    │                     │                   │
     │                 │                    │                     │                   │
     │                 │  analyze_task()    │                     │                   │
     │                 │───────────────────>│                     │                   │
     │                 │                    │                     │                   │
     │                 │                    │  classify(task)     │                   │
     │                 │                    │────────────────────>│                   │
     │                 │                    │                     │                   │
     │                 │                    │                     │ ┌───────────────┐ │
     │                 │                    │                     │ │ Confidence    │ │
     │                 │                    │                     │ │   < 0.6       │ │
     │                 │                    │                     │ │ (LOW)         │ │
     │                 │                    │                     │ └───────────────┘ │
     │                 │                    │                     │                   │
     │                 │                    │                     │  "Classify this   │
     │                 │                    │                     │   task given      │
     │                 │                    │                     │   servers..."     │
     │                 │                    │                     │──────────────────>│
     │                 │                    │                     │                   │
     │                 │                    │                     │  {servers:        │
     │                 │                    │                     │   [a, b, c],      │
     │                 │                    │                     │   reasoning: ...} │
     │                 │                    │                     │<──────────────────│
     │                 │                    │                     │                   │
     │                 │                    │  {servers, conf=0.9}│                   │
     │                 │                    │<────────────────────│                   │
     │                 │                    │                     │                   │
     │                 │  {recommended,     │                     │                   │
     │                 │   llm_assisted}    │                     │                   │
     │                 │<───────────────────│                     │                   │
     │                 │                    │                     │                   │
     ▼                 ▼                    ▼                     ▼                   ▼
```

---

## 14. Decision Matrix

### 14.1 Выбор основного подхода классификации

Для принятия решения о выборе основного подхода используется взвешенная матрица:

| Критерий | Вес | Rule-Based | LLM-only | Semantic | Hybrid (Rec.) |
|----------|-----|------------|----------|----------|---------------|
| **Точность** | 25% | 2 | 5 | 4 | 4.5 |
| **Latency** | 20% | 5 | 1 | 4 | 4 |
| **Cost** | 15% | 5 | 1 | 5 | 4 |
| **Масштабируемость** | 15% | 2 | 4 | 5 | 5 |
| **Maintainability** | 10% | 2 | 4 | 4 | 3 |
| **Offline capability** | 10% | 5 | 1 | 5 | 4 |
| **Adaptability** | 5% | 1 | 5 | 4 | 4 |
| **Weighted Score** | 100% | **3.15** | **2.80** | **4.35** | **4.20** |

**Вывод:** Semantic подход с Hybrid fallback — оптимальный выбор.

### 14.2 Выбор Embedding модели

| Модель | Размер | Latency (CPU) | Quality | Рекомендация |
|--------|--------|---------------|---------|--------------|
| all-MiniLM-L6-v2 | 80MB | 15ms | Good | ✅ **MVP** |
| all-mpnet-base-v2 | 420MB | 50ms | Better | ⚠️ Production |
| text-embedding-3-small | API | 200ms | Best | ❌ Cloud only |
| bge-small-en-v1.5 | 130MB | 20ms | Better | ✅ Alternative |

---

## Приложения

### A. Примеры конфигурации

#### A.1 Конфигурация Orchestrator MCP Server

```yaml
# ~/.docker/mcp-orchestrator/config.yaml

orchestrator:
  version: "1.0"
  
  # Classification settings
  classification:
    # Веса для hybrid scoring
    pattern_weight: 0.4
    semantic_weight: 0.6
    
    # Пороги
    confidence_threshold: 0.6
    llm_fallback_threshold: 0.5
    
    # Ограничения
    max_servers: 5
    max_tools: 100
    max_tokens: 10000
    
  # Embedding model
  embedding:
    model: "all-MiniLM-L6-v2"
    cache_embeddings: true
    cache_ttl: 86400  # 24 hours
    
  # LLM fallback (optional)
  llm_fallback:
    enabled: true
    provider: "openai"  # or "anthropic"
    model: "gpt-4o-mini"
    timeout: 5000
    
  # Session management
  session:
    cache_enabled: true
    cache_ttl: 3600  # 1 hour
    learning_enabled: true
    
  # Logging
  logging:
    level: "INFO"
    log_tool_calls: true
    log_classifications: true
    metrics_enabled: true
```

#### A.2 Пример Server Registry Entry

```yaml
# ~/.docker/mcp-orchestrator/registry/servers/postgres.yaml

server:
  name: postgres
  display_name: "PostgreSQL MCP Server"
  docker_image: "mcp/postgres:latest"
  
  semantic:
    description: |
      PostgreSQL database management including queries, schema inspection,
      migrations, performance analysis, and database administration tasks.
    
    keywords:
      - postgres
      - postgresql
      - database
      - sql
      - query
      - migration
      - schema
      - table
      - index
      - transaction
      - backup
      - restore
    
    capabilities:
      - database_management
      - sql_execution
      - schema_inspection
      - data_migration
    
    example_tasks:
      - "Run SQL query"
      - "Check database schema"
      - "Analyze query performance"
      - "Create database migration"
      - "Backup database"
      - "List all tables"
  
  tools:
    count: 28
    categories:
      queries: 8
      schema: 10
      admin: 6
      migrations: 4
    
    highlights:
      - execute_query
      - describe_table
      - list_tables
      - create_migration
  
  relations:
    requires: []
    recommends:
      - filesystem  # For migration files
    conflicts: []
  
  metadata:
    token_cost_estimate: 2800
    startup_time_ms: 1500
    memory_mb: 128
    requires_secrets:
      - POSTGRES_CONNECTION_STRING
```

#### A.3 Cursor MCP Configuration

```json
// ~/.cursor/mcp.json

{
  "mcpServers": {
    "docker-mcp-orchestrator": {
      "command": "docker",
      "args": [
        "mcp", "gateway", "run",
        "--servers", "orchestrator"
      ],
      "env": {
        "ORCHESTRATOR_CONFIG": "~/.docker/mcp-orchestrator/config.yaml"
      }
    }
  }
}
```

#### A.4 Profile Definition

```yaml
# ~/.docker/mcp-orchestrator/profiles/web-development.yaml

profile:
  name: web-development
  display_name: "Full-Stack Web Development"
  description: |
    Profile for full-stack web development with Git version control,
    database management, and file system access.
  
  servers:
    required:
      - github
      - filesystem
    optional:
      - postgres
      - redis
      - browser
  
  # Auto-detection rules
  detection:
    files:
      - pattern: "package.json"
        boost: 0.3
      - pattern: "*.tsx"
        boost: 0.2
      - pattern: "docker-compose.yml"
        boost: 0.2
    
    git_remotes:
      - pattern: "github.com"
        boost: 0.3
  
  # Token budget for this profile
  constraints:
    max_tools: 80
    max_tokens: 8000
```

---

### B. Глоссарий

| Термин | Определение |
|--------|-------------|
| **MCP** | Model Context Protocol — протокол для подключения tools к AI |
| **Tool** | Функция/команда, доступная AI через MCP |
| **Server** | MCP сервер, предоставляющий набор tools |
| **Gateway** | Docker MCP Gateway — прокси для управления серверами |
| **Context Window** | Ограниченное "окно" токенов, доступное AI |
| **Embedding** | Векторное представление текста для семантического поиска |
| **Two-Phase Router** | Архитектурный паттерн с разделением на фазы классификации и выполнения |
| **Meta-Tool** | Инструмент оркестратора для управления другими серверами |
| **Token Budget** | Ограничение на количество токенов для описания tools |
| **Reconnect** | Переподключение MCP для обновления списка доступных tools |

### C. FAQ (Frequently Asked Questions)

#### Q1: Почему нельзя просто использовать меньше MCP серверов?

**A:** Разработчики часто работают над разнородными задачами в течение дня: код-ревью (GitHub), работа с БД (Postgres), тестирование (Browser), деплой (K8s). Ручное переключение между конфигурациями:
- Отнимает время
- Создаёт когнитивную нагрузку  
- Приводит к ошибкам

Оркестратор автоматизирует этот процесс.

#### Q2: Как часто происходит reconnect?

**A:** При оптимальной работе:
- 1 reconnect в начале сессии (после классификации первой задачи)
- Дополнительные reconnects только при смене контекста работы

Цель: **< 2 reconnects за типичную сессию работы**.

#### Q3: Что если классификатор ошибётся?

**A:** Многоуровневая защита:
1. AI может вызвать `switch_context()` для запроса дополнительных серверов
2. Пользователь может использовать профили для override
3. Система учится на паттернах использования
4. Low-confidence решения направляются на LLM-fallback

#### Q4: Как добавить новый MCP сервер в систему?

**A:** 
1. Добавьте сервер в Docker MCP Catalog: `docker mcp catalog add`
2. Создайте YAML-файл в `~/.docker/mcp-orchestrator/registry/servers/`
3. Сгенерируйте embedding: `orchestrator registry update`
4. Сервер автоматически станет доступен для классификации

#### Q5: Можно ли использовать без Docker MCP Toolkit?

**A:** Архитектура спроектирована с абстракцией Server Lifecycle Manager. Теоретически можно реализовать адаптеры для:
- Native MCP процессов
- Kubernetes-based MCP
- Remote MCP серверов

Но MVP фокусируется на Docker MCP Toolkit как primary backend.

#### Q6: Какие данные отправляются в LLM при fallback?

**A:**
- Описание задачи (user input)
- Список доступных серверов (names + short descriptions)
- НЕ отправляются: credentials, код проекта, history

Privacy-first подход.

### D. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Low classification accuracy | Medium | High | A/B testing, continuous learning, LLM fallback |
| Reconnect delays frustrate users | Medium | Medium | Predictive loading, session caching |
| Docker MCP CLI changes break integration | Low | High | Version pinning, integration tests |
| Embedding model produces poor results | Low | Medium | Multiple model options, manual overrides |
| Token budget exceeded | Low | Medium | Hard limits, graceful degradation |
| Cold start performance | Medium | Low | Precomputed embeddings, warm-up |

### E. Ссылки

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Docker MCP Toolkit Documentation](https://docs.docker.com/desktop/mcp/)
- [Sentence Transformers](https://www.sbert.net/)
- [FastMCP Python SDK](https://github.com/jlowin/fastmcp)

---

*Документ подготовлен командой архитекторов. Для вопросов и предложений создавайте issues в репозитории.*
