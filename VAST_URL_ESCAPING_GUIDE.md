# Руководство по экранированию URL для VAST документов

## Проблема

При валидации VAST XML документов возникает ошибка:
```
XML Parser Error: The reference to entity "c" must end with the ';' delimiter.
```

**Причина:** В XML символ `&` должен быть экранирован как `&amp;`. Если в URL есть неэкранированные символы `&`, XML парсер пытается интерпретировать их как начало entity (например, `&c`), что вызывает ошибку.

## Решение

Используйте функцию `escape_vast_url()` из модуля `src.orchestrator.utils` для экранирования всех URL перед подстановкой в VAST документ.

## Использование

### Базовый пример

```python
from src.orchestrator.utils import escape_vast_url

# ❌ НЕПРАВИЛЬНО - вызовет ошибку парсера
url = "https://example.com?param1=value1&param2=value2"
vast_xml = f'<Impression>{url}</Impression>'

# ✅ ПРАВИЛЬНО - экранирует специальные символы
url = "https://example.com?param1=value1&param2=value2"
escaped_url = escape_vast_url(url)
vast_xml = f'<Impression>{escaped_url}</Impression>'
# Результат: <Impression>https://example.com?param1=value1&amp;param2=value2</Impression>
```

### Примеры из реального VAST документа

```python
from src.orchestrator.utils import escape_vast_url

# Impression URL
impression_url = "https://bs.serving-sys.ru/Serving/adServer.bs?cn=display&c=25&pli=1087731545"
escaped = escape_vast_url(impression_url)
# Результат: https://bs.serving-sys.ru/Serving/adServer.bs?cn=display&amp;c=25&amp;pli=1087731545

# Tracking URL
tracking_url = "https://px385.mhverifier.ru/s.gif?&mh_camp=123&event=start"
escaped = escape_vast_url(tracking_url)
# Результат: https://px385.mhverifier.ru/s.gif?&amp;mh_camp=123&amp;event=start

# Error URL с макросом
error_url = "https://example.com/error.gif?code=[ERRORCODE]"
escaped = escape_vast_url(error_url)
# Результат: https://example.com/error.gif?code=[ERRORCODE] (без изменений, т.к. нет &)
```

### Генерация VAST элементов

```python
from src.orchestrator.utils import escape_vast_url, validate_and_escape_vast_url

def create_impression_element(url: str, impression_id: str = None) -> str:
    """Создать элемент Impression с экранированным URL."""
    escaped_url = escape_vast_url(url)
    if impression_id:
        return f'<Impression id="{impression_id}">{escaped_url}</Impression>'
    return f'<Impression>{escaped_url}</Impression>'

def create_tracking_element(url: str, event: str) -> str:
    """Создать элемент Tracking с экранированным URL."""
    escaped_url = escape_vast_url(url)
    return f'<Tracking event="{event}">{escaped_url}</Tracking>'

# Использование
impression = create_impression_element(
    "https://example.com?param=1&id=2",
    impression_id="AdServing"
)

tracking = create_tracking_element(
    "https://example.com/track?event=start&id=123",
    event="start"
)
```

### Обработка пустых значений

```python
from src.orchestrator.utils import validate_and_escape_vast_url

# Автоматически обрабатывает None и пустые строки
url1 = validate_and_escape_vast_url("https://example.com?p=1&q=2")
# Результат: "https://example.com?p=1&amp;q=2"

url2 = validate_and_escape_vast_url(None)
# Результат: None

url3 = validate_and_escape_vast_url("")
# Результат: None
```

## Доступные функции

### `escape_vast_url(url: str) -> str`
Основная функция для экранирования URL в VAST документах.
- Экранирует: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`
- Возвращает исходную строку, если URL пустой

### `escape_xml_url(url: str) -> str`
Алиас для `escape_vast_url()` (более общее название).

### `escape_xml_url_advanced(url: str, escape_quotes: bool = False) -> str`
Расширенная версия с опциональным экранированием кавычек.
- Полезно, если URL используется в XML атрибутах

### `validate_and_escape_vast_url(url: Optional[str]) -> Optional[str]`
Валидирует и экранирует URL, возвращает `None` для пустых значений.

## Что экранируется

| Символ | Экранирование | Пример |
|--------|---------------|--------|
| `&` | `&amp;` | `param=1&id=2` → `param=1&amp;id=2` |
| `<` | `&lt;` | `query=<test>` → `query=&lt;test&gt;` |
| `>` | `&gt;` | `query=<test>` → `query=&lt;test&gt;` |

**Важно:** URL-кодирование (например, `%20` для пробела) НЕ изменяется. Функция экранирует только XML-специальные символы.

## Где применять

Экранируйте URL во всех элементах VAST, которые содержат URL:
- `<Error>`
- `<Impression>`
- `<Tracking>` (все события)
- `<ClickThrough>`
- `<ClickTracking>`
- `<MediaFile>` (URL медиафайла)

## Тестирование

Запустите тестовый скрипт для проверки:
```bash
python3 test_vast_url_escaping.py
```

## Примечания

1. **Не экранируйте дважды:** Если URL уже экранирован, повторное экранирование создаст `&amp;amp;`
2. **Макросы VAST:** Макросы типа `[ERRORCODE]` не изменяются
3. **URL-кодирование:** Процентное кодирование (`%20`, `%7E` и т.д.) сохраняется как есть
