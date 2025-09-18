# Изменения в конфигурации браузера

## Дата: 2025-09-18 17:45:00

### ✅ Выполнено

1. **Добавлена секция управления браузером в config.py:**
   - `MAX_PARALLEL_BROWSERS = 3` - управление количеством параллельных браузеров
   - `HEADLESS_MODE = True` - включение/отключение headless режима  
   - `BATCH_SIZE = 450` - размер группы EAN кодов для обработки
   - `BROWSER_TIMEOUTS` - настройки таймаутов для различных операций
   - `RETRY_SETTINGS` - параметры повторных попыток

2. **Обновлены функции в tradewatch_login.py:**
   - Добавлен импорт `import config`
   - Изменены дефолтные параметры с `headless=True/False` на `headless=None`
   - Добавлена логика использования конфигурации: `if headless is None: headless = config.HEADLESS_MODE`
   - Заменены hardcoded значения `batch_size = 450` на `batch_size = config.BATCH_SIZE`
   - Заменены hardcoded значения `max_parallel=4` на `max_parallel=config.MAX_PARALLEL_BROWSERS`

3. **Обновленные функции:**
   - `process_supplier_file_with_tradewatch()`
   - `process_supplier_file_with_tradewatch_old_version()`
   - `process_supplier_file_with_tradewatch_interruptible()`
   - `process_supplier_file_with_tradewatch_single_browser()`
   - `process_ean_codes_batch()`
   - `process_batch_with_new_browser()`
   - `process_multiple_batches_parallel()`
   - `initialize_browser_and_login()`
   - `process_batch_in_separate_browser_with_unique_name()`

4. **Исправлены hardcoded значения:**
   - Заменено `max_parallel=4` на `config.MAX_PARALLEL_BROWSERS`
   - Заменены дефолтные значения `headless=False` на `headless=None`
   - Обновлены комментарии для отражения использования конфигурации

### 🎯 Результат

Теперь управление браузерами полностью централизовано в файле `config.py`:

```python
# Изменение количества браузеров
config.MAX_PARALLEL_BROWSERS = 2  # Уменьшить нагрузку

# Включение headless режима
config.HEADLESS_MODE = True  # Для продакшена

# Изменение размера групп
config.BATCH_SIZE = 300  # Меньшие группы для стабильности
```

### 🔧 Совместимость

- Все существующие вызовы функций остаются рабочими
- При передаче явного параметра `headless=True/False` он имеет приоритет над конфигом
- При `headless=None` или без указания параметра используется `config.HEADLESS_MODE`
- При `max_parallel=None` или без указания параметра используется `config.MAX_PARALLEL_BROWSERS`

### 🐛 Исправленные проблемы

- **Проблема**: Использовались hardcoded значения `max_parallel=4` вместо конфигурации
- **Решение**: Заменены на `config.MAX_PARALLEL_BROWSERS` во всех местах
- **Проблема**: Некоторые функции имели `headless=False` по умолчанию
- **Решение**: Изменены на `headless=None` с fallback на `config.HEADLESS_MODE`