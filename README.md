# pii-filter-service

Локальный HTTP-сервис деперсонализации текста для закрытой корпоративной сети. n8n отправляет текст в `/mask`, сервис локально маскирует PII через regex-слой и OpenAI Privacy Filter, а наружу в OpenRouter уходит только `masked_text`.

## Как работает

Порядок обработки:

1. Regex layer находит российские и корпоративные идентификаторы: email, телефон, ИНН, КПП, СНИЛС, ОГРН, договоры, внутренние URL/IP, счета, БИК, паспорт, табельный номер.
2. OpenAI Privacy Filter находит контекстные сущности: `private_person`, `private_phone`, `private_email`, `private_address`, `private_date`, `private_url`, `account_number`, `secret`.
3. Пересекающиеся spans объединяются: остаётся более длинный, при равной длине regex имеет приоритет.
4. Замены выполняются справа налево, чтобы не ломать индексы.

OpenAI Privacy Filter запускается локально. Сервис использует Python API `opf._api.OPF`, а если он недоступен, аккуратно пытается вызвать `python -m opf` через subprocess. Checkpoint задаётся через `OPF_CHECKPOINT` или `MODEL_PATH`, устройство через `DEVICE=cpu|cuda`.

## Модель в закрытом контуре

На машине с интернетом скачайте checkpoint OpenAI Privacy Filter из `https://huggingface.co/openai/privacy-filter` и перенесите файлы в закрытый контур, например в `./models/privacy_filter`.

Также установите код OpenAI Privacy Filter из `https://github.com/openai/privacy-filter` в окружение сервиса:

```bash
git clone https://github.com/openai/privacy-filter /opt/privacy-filter
pip install -e /opt/privacy-filter
```

В Docker-образе для production обычно копируют внутренний mirror в `vendor/privacy-filter` и раскомментируют установку в `Dockerfile`.

## Локальный запуск

```bash
cd depersonalization
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -e /opt/privacy-filter
uvicorn app.main:app --host 127.0.0.1 --port 8088
```

Для smoke-тестов без модели:

```bash
MODEL_ENABLED=false ALLOW_NO_AUTH=true uvicorn app.main:app --host 127.0.0.1 --port 8088
```

## Docker

```bash
cd depersonalization
cp .env.example .env
docker compose up --build
```

Compose публикует сервис только на `127.0.0.1:8088` и монтирует модель:

```yaml
./models/privacy_filter:/app/models/privacy_filter
```

## API

Health:

```bash
curl http://127.0.0.1:8088/health
```

Mask:

```bash
curl -X POST http://127.0.0.1:8088/mask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{
    "text": "Позвони Ивану Петрову +7 999 123-45-67, email ivan.petrov@etm.ru, договор ETM-4421",
    "return_entities": true
  }'
```

Batch:

```bash
curl -X POST http://127.0.0.1:8088/mask/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"items":[{"id":"msg_1","text":"email ivan.petrov@etm.ru"}],"return_entities":true}'
```

## n8n

HTTP Request node:

- Method: `POST`
- URL: `http://pii-filter:8088/mask`
- Header: `X-API-Key: change-me`
- JSON body: `{"text": "{{$json.chatInput}}", "return_entities": false}`
- В OpenRouter передавайте только `{{$json.masked_text}}`.

Пример flow:

1. Chat Trigger
2. HTTP Request `POST http://pii-filter:8088/mask`
3. OpenRouter node/API получает только `masked_text`

## Security

- Не логируйте исходный текст и реальные значения PII.
- Используйте `PII_FILTER_API_KEY` и заголовок `X-API-Key`.
- Не публикуйте порт наружу; compose уже слушает только `127.0.0.1`.
- Держите сервис в одной Docker network с n8n.
- По возможности отключите сохранение sensitive execution data в n8n.
- `RETURN_RAW_ENTITIES_ALLOWED=false` по умолчанию, поэтому реальные значения PII не возвращаются даже при запросе клиента.
- `MAX_TEXT_LENGTH` ограничивает размер входного текста, при превышении возвращается `413`.
- CORS выключен по умолчанию.

## Limitations

- Деперсонализация не гарантирует 100% удаление персональных данных.
- OpenAI Privacy Filter может ошибаться на русском и доменных данных.
- Нужно тестировать качество на корпоративных примерах.
- Regex-правила нужно адаптировать под реальные форматы компании.

## Тесты и линтинг

```bash
make test
make lint
```

Тесты запускаются с `MODEL_ENABLED=false`, чтобы проверять API, безопасность логов и regex-слой без загрузки тяжёлой модели.
