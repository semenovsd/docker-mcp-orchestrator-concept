# Руководство по экранированию URL для VAST документов

## Проблема

При вставке URL с параметрами запроса в VAST XML документы возникает ошибка парсера:
```
XML Parser Error: The reference to entity "c" must end with the ';' delimiter.
```

**Причина:** Символ `&` в URL интерпретируется XML-парсером как начало entity reference (например, `&amp;`, `&lt;`). Если за `&` не следует валидная entity, парсер выдает ошибку.

## Решение

Используйте функцию `escape_url_for_xml()` из модуля `src.orchestrator.utils` для экранирования всех URL перед вставкой в VAST документ.

### Пример использования

```python
from src.orchestrator.utils import escape_url_for_xml

# Исходный URL с неэкранированными амперсандами
impression_url = "https://bs.serving-sys.ru/Serving/adServer.bs?cn=display&c=25&pli=1087731545"

# Экранируем URL перед вставкой в XML
escaped_url = escape_url_for_xml(impression_url)
# Результат: "https://bs.serving-sys.ru/Serving/adServer.bs?cn=display&amp;c=25&amp;pli=1087731545"

# Теперь безопасно используем в VAST XML
vast_xml = f'''<VAST version="3.0">
  <Ad>
    <InLine>
      <Impression>{escaped_url}</Impression>
    </InLine>
  </Ad>
</VAST>'''
```

### Где применять экранирование

Экранируйте **все** URL в следующих элементах VAST:

- `<Error>` - URL для отслеживания ошибок
- `<Impression>` - URL для отслеживания показов
- `<Tracking>` - URL для отслеживания событий (start, firstQuartile, midpoint, thirdQuartile, complete, и т.д.)
- `<ClickThrough>` - URL для перехода по клику
- `<ClickTracking>` - URL для отслеживания кликов
- `<MediaFile>` - URL медиафайлов (обычно не содержат `&`, но лучше экранировать)
- Любые другие элементы, содержащие URL

### Пример полного использования

```python
from src.orchestrator.utils import escape_url_for_xml

def build_vast_xml(ad_data):
    """Строит VAST XML документ с правильно экранированными URL."""
    
    # Экранируем все URL
    error_url = escape_url_for_xml(ad_data['error_url'])
    impression_url = escape_url_for_xml(ad_data['impression_url'])
    tracking_start = escape_url_for_xml(ad_data['tracking_start_url'])
    click_through = escape_url_for_xml(ad_data['click_through_url'])
    
    vast_xml = f'''<VAST version="3.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Ad id="{ad_data['ad_id']}">
    <InLine>
      <AdSystem>{ad_data['ad_system']}</AdSystem>
      <AdTitle>{ad_data['ad_title']}</AdTitle>
      <Error>{error_url}</Error>
      <Impression>{impression_url}</Impression>
      <Creatives>
        <Creative>
          <Linear>
            <TrackingEvents>
              <Tracking event="start">{tracking_start}</Tracking>
            </TrackingEvents>
            <VideoClicks>
              <ClickThrough>{click_through}</ClickThrough>
            </VideoClicks>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>'''
    
    return vast_xml
```

### Важные замечания

1. **Не двойное экранирование:** Функция автоматически определяет уже экранированные entity references (`&amp;`, `&lt;`, и т.д.) и не экранирует их повторно.

2. **Производительность:** Функция использует регулярные выражения и работает быстро даже для длинных URL.

3. **Безопасность:** Функция экранирует только символы `&`, которые не являются частью валидных XML entities. Остальные символы URL остаются без изменений.

4. **Совместимость:** Решение соответствует спецификации VAST 3.0 и стандартам XML.

### Тестирование

Запустите тестовый скрипт для проверки:
```bash
python3 test_url_escape.py
```

## Альтернативные решения

Если вы используете библиотеку для генерации XML (например, `xml.etree.ElementTree` или `lxml`), она может автоматически экранировать символы. Однако, для явного контроля и совместимости с различными парсерами рекомендуется использовать `escape_url_for_xml()`.
