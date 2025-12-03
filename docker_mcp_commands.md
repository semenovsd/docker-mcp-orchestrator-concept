# Docker MCP Toolkit - Полный список команд

Docker MCP Toolkit's CLI - Управление MCP серверами и клиентами.

## Основные команды

### `docker mcp [OPTIONS]`

Основная команда для работы с Docker MCP Toolkit.

**Флаги:**
- `-v, --version` - Вывести информацию о версии и выйти

---

## catalog - Управление каталогами MCP серверов

### `docker mcp catalog`

Управление каталогами MCP серверов.

#### `docker mcp catalog add <catalog> <server-name> <catalog-file>`

Добавить сервер в каталог.

**Флаги:**
- `--force` - Перезаписать существующий сервер в каталоге

**Примеры:**
```bash
# Добавить сервер из другого файла каталога
docker mcp catalog add my-catalog github-server ./github-catalog.yaml

# Добавить с перезаписью существующего сервера
docker mcp catalog add my-catalog slack-bot ./team-catalog.yaml --force
```

#### `docker mcp catalog bootstrap <output-file-path>`

Создать стартовый файл каталога с примерами серверов Docker и Docker Hub.

#### `docker mcp catalog create <name>`

Создать новый пустой каталог.

**Примеры:**
```bash
# Создать новый каталог для серверов разработки
docker mcp catalog create dev-servers

# Создать каталог для инструментов мониторинга продакшена
docker mcp catalog create prod-monitoring
```

#### `docker mcp catalog export <catalog-name> <file-path>`

Экспортировать настроенный каталог в файл.

#### `docker mcp catalog fork <src-catalog> <new-name>`

Создать копию существующего каталога.

**Примеры:**
```bash
# Форкнуть каталог Docker для кастомизации
docker mcp catalog fork docker-mcp my-custom-docker

# Форкнуть командный каталог для личного использования
docker mcp catalog fork team-servers my-servers
```

#### `docker mcp catalog import <alias|url|file>`

Импортировать каталог из URL или файла.

**Флаги:**
- `--dry-run` - Показать импортированные данные, но не обновлять каталог
- `--mcp-registry string` - Импортировать сервер из MCP registry URL в существующий каталог

**Примеры:**
```bash
# Импортировать из URL
docker mcp catalog import https://example.com/my-catalog.yaml

# Импортировать из локального файла
docker mcp catalog import ./shared-catalog.yaml

# Импортировать из MCP registry URL в существующий каталог
docker mcp catalog import my-catalog --mcp-registry https://registry.example.com/server
```

#### `docker mcp catalog init`

Инициализировать систему каталогов.

**Примеры:**
```bash
# Инициализировать систему каталогов
docker mcp catalog init
```

#### `docker mcp catalog ls`

Список всех настроенных каталогов.

**Флаги:**
- `--format format` - Формат вывода. Поддерживается: "json", "yaml"

**Примеры:**
```bash
# Список всех каталогов
docker mcp catalog ls

# Список каталогов в формате JSON
docker mcp catalog ls --format=json
```

#### `docker mcp catalog reset`

Сбросить систему каталогов.

**Примеры:**
```bash
# Сбросить все пользовательские каталоги
docker mcp catalog reset
```

#### `docker mcp catalog rm <name>`

Удалить каталог.

**Примеры:**
```bash
# Удалить каталог
docker mcp catalog rm old-servers
```

#### `docker mcp catalog show [name]`

Отобразить содержимое каталога.

**Флаги:**
- `--format format` - Поддерживается: "json", "yaml"

**Примеры:**
```bash
# Показать официальный каталог Docker
docker mcp catalog show

# Показать конкретный каталог в формате JSON
docker mcp catalog show my-catalog --format=json
```

#### `docker mcp catalog update [name]`

Обновить каталог(и) из удаленных источников.

**Примеры:**
```bash
# Обновить все каталоги
docker mcp catalog update

# Обновить конкретный каталог
docker mcp catalog update team-servers
```

---

## client - Управление MCP клиентами

### `docker mcp client`

Управление MCP клиентами.

Поддерживаемые клиенты: amazon-q, claude-code, claude-desktop, codex, continue, cursor, gemini, goose, gordon, lmstudio, opencode, sema4, vscode, zed

#### `docker mcp client connect [OPTIONS] <mcp-client>`

Подключить Docker MCP Toolkit к клиенту.

**Флаги:**
- `-g, --global` - Изменить системную конфигурацию или настройки клиентов в текущем git репозитории
- `-q, --quiet` - Отображать только ошибки

#### `docker mcp client disconnect [OPTIONS] <mcp-client>`

Отключить Docker MCP Toolkit от клиента.

**Флаги:**
- `-g, --global` - Изменить системную конфигурацию или настройки клиентов в текущем git репозитории
- `-q, --quiet` - Отображать только ошибки

#### `docker mcp client ls`

Список конфигураций клиентов.

**Флаги:**
- `-g, --global` - Изменить системную конфигурацию или настройки клиентов в текущем git репозитории
- `--json` - Вывести в формате JSON

---

## config - Управление конфигурацией

### `docker mcp config`

Управление конфигурацией.

#### `docker mcp config read`

Прочитать конфигурацию.

#### `docker mcp config reset`

Сбросить конфигурацию.

#### `docker mcp config write`

Записать конфигурацию.

---

## feature - Управление экспериментальными функциями

### `docker mcp feature`

Управление экспериментальными функциями.

#### `docker mcp feature disable <feature-name>`

Отключить экспериментальную функцию.

#### `docker mcp feature enable <feature-name>`

Включить экспериментальную функцию.

#### `docker mcp feature ls`

Список всех доступных функций и их статус.

---

## gateway - Управление MCP Server gateway

### `docker mcp gateway`

Управление MCP Server gateway.

#### `docker mcp gateway run`

Запустить gateway.

**Флаги:**
- `--additional-catalog strings` - Дополнительные пути к каталогам для добавления к каталогам по умолчанию
- `--additional-config strings` - Дополнительные пути к конфигурациям для объединения с config.yaml по умолчанию
- `--additional-registry strings` - Дополнительные пути к реестрам для объединения с registry.yaml по умолчанию
- `--additional-tools-config strings` - Дополнительные пути к инструментам для объединения с tools.yaml по умолчанию
- `--block-network` - Блокировать доступ инструментов к запрещенным сетевым ресурсам
- `--block-secrets` - Блокировать секреты от отправки/получения в/из инструментов (по умолчанию true)
- `--catalog strings` - Пути к каталогам docker (абсолютные или относительно ~/.docker/mcp/catalogs/) (по умолчанию [docker-mcp.yaml])
- `--config strings` - Пути к файлам конфигурации (абсолютные или относительно ~/.docker/mcp/) (по умолчанию [config.yaml])
- `--cpus int` - CPU, выделенные каждому MCP серверу (по умолчанию 1) (по умолчанию 1)
- `--debug-dns` - Отладка разрешения DNS
- `--dry-run` - Запустить gateway, но не слушать подключения (полезно для тестирования конфигурации)
- `--enable-all-servers` - Включить все серверы в каталоге (вместо использования отдельных опций --servers)
- `--interceptor stringArray` - Список перехватчиков для использования (формат: when:type:path, например 'before:exec:/bin/path')
- `--log-calls` - Логировать вызовы инструментов (по умолчанию true)
- `--long-lived` - Контейнеры долгоживущие и не будут удалены до остановки gateway, полезно для серверов с состоянием
- `--mcp-registry strings` - URL реестров MCP для получения серверов (можно повторять)
- `--memory string` - Память, выделенная каждому MCP серверу (по умолчанию 2Gb) (по умолчанию "2Gb")
- `--oci-ref stringArray` - Ссылки на OCI образы для использования
- `--port int` - TCP порт для прослушивания (по умолчанию прослушивание на stdio)
- `--registry strings` - Пути к файлам реестра (абсолютные или относительно ~/.docker/mcp/) (по умолчанию [registry.yaml])
- `--secrets docker-desktop` - Разделенные двоеточием пути для поиска секретов. Может быть docker-desktop или путь к .env файлу (по умолчанию используется API секретов Docker Desktop) (по умолчанию "docker-desktop")
- `--servers strings` - Имена серверов для включения (если не пусто, игнорировать флаг --registry)
- `--session string` - Имя сессии для загрузки и сохранения конфигурации из ~/.docker/mcp/{SessionName}/
- `--static` - Включить статический режим (также известный как предзапущенные серверы)
- `--tools strings` - Список инструментов для включения
- `--tools-config strings` - Пути к файлам инструментов (абсолютные или относительно ~/.docker/mcp/) (по умолчанию [tools.yaml])
- `--transport string` - stdio, sse или streaming. Использует переменную окружения MCP_GATEWAY_AUTH_TOKEN для аутентификации localhost для предотвращения атак dns rebinding (по умолчанию "stdio")
- `--verbose` - Подробный вывод
- `--verify-signatures` - Проверять подписи образов серверов
- `--watch` - Отслеживать изменения и перенастраивать gateway (по умолчанию true)

---

## policy - Управление политиками секретов

### `docker mcp policy`

Управление политиками секретов.

#### `docker mcp policy dump`

Вывести содержимое политики.

#### `docker mcp policy set <content>`

Установить политику для управления секретами в Docker Desktop.

**Примеры:**
```bash
### Создать резервную копию текущей политики в файл
docker mcp policy dump > policy.conf

### Установить новую политику
docker mcp policy set "my-secret allows postgres"

### Восстановить предыдущую политику
cat policy.conf | docker mcp policy set
```

---

## secret - Управление секретами

### `docker mcp secret`

Управление секретами.

#### `docker mcp secret ls`

Список всех имен секретов в хранилище секретов Docker Desktop.

**Флаги:**
- `--json` - Вывести в формате JSON

#### `docker mcp secret rm name1 name2 ...`

Удалить секреты из хранилища секретов Docker Desktop.

**Флаги:**
- `--all` - Удалить все секреты

#### `docker mcp secret set key[=value]`

Установить секрет в хранилище секретов Docker Desktop.

**Флаги:**
- `--provider string` - Поддерживается: credstore, oauth/<provider>

**Примеры:**
```bash
### Использовать секреты для пароля postgres с политикой по умолчанию

> docker mcp secret set POSTGRES_PASSWORD=my-secret-password
> docker run -d -l x-secret:POSTGRES_PASSWORD=/pwd.txt -e POSTGRES_PASSWORD_FILE=/pwd.txt -p 5432 postgres

### Передать секрет через STDIN

> echo my-secret-password > pwd.txt
> cat pwd.txt | docker mcp secret set POSTGRES_PASSWORD
```

---

## server - Управление серверами

### `docker mcp server`

Управление серверами.

#### `docker mcp server disable`

Отключить сервер или несколько серверов.

#### `docker mcp server enable`

Включить сервер или несколько серверов.

#### `docker mcp server init <directory>`

Инициализировать новый проект MCP сервера.

**Флаги:**
- `--language string` - Язык программирования для сервера (в настоящее время поддерживается только 'go') (по умолчанию "go")
- `--template string` - Шаблон для использования (basic, chatgpt-app-basic) (по умолчанию "basic")

#### `docker mcp server inspect`

Получить информацию о сервере или проверить OCI артефакт.

#### `docker mcp server ls`

Список включенных серверов.

**Флаги:**
- `--json` - Вывод в формате JSON

#### `docker mcp server reset`

Отключить все серверы.

---

## tools - Управление инструментами

### `docker mcp tools`

Управление инструментами.

**Флаги:**
- `--format string` - Формат вывода (json|list) (по умолчанию "list")
- `--gateway-arg strings` - Дополнительные аргументы, передаваемые в gateway
- `--verbose` - Подробный вывод
- `--version string` - Версия gateway (по умолчанию "2")

#### `docker mcp tools call`

Вызвать инструмент.

#### `docker mcp tools count`

Подсчитать количество инструментов.

#### `docker mcp tools disable [tool1] [tool2] ...`

Отключить один или несколько инструментов.

**Флаги:**
- `--server string` - Указать, какой сервер предоставляет инструменты (необязательно, будет автоматически обнаружен, если не указан)

#### `docker mcp tools enable [tool1] [tool2] ...`

Включить один или несколько инструментов.

**Флаги:**
- `--server string` - Указать, какой сервер предоставляет инструменты (необязательно, будет автоматически обнаружен, если не указан)

#### `docker mcp tools inspect`

Проверить инструмент.

#### `docker mcp tools ls`

Список инструментов.

---

## version - Информация о версии

### `docker mcp version`

Показать информацию о версии.

---

## Примечания

- Все команды поддерживают стандартные флаги Docker CLI
- Большинство команд поддерживают вывод в формате JSON через флаг `--json` или `--format json`
- Конфигурационные файлы обычно находятся в `~/.docker/mcp/`
- Каталоги обычно находятся в `~/.docker/mcp/catalogs/`

