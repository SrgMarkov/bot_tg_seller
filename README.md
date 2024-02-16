# Телеграм бот - продажи

Скелет бота по продаже товаров через ТГ

## Как установить
Для работы бота и crm интернет магазина необходим Python версии не ниже 3.8, а так же [node.js](https://nodejs.org/en/) версии не ниже 18.16

Первым делом необходимо установить [strapi](https://github.com/strapi/strapi?tab=readme-ov-file), CRM для интернет магазина

```sh
npx create-strapi-app@latest seller_crm --quickstart
```

Папку `api` в корне проекта необходимо переместить с заменой в `celler_crm/src/` для импорта структуры данных

После установки crm откроется окно создания администратора. После чего наполните CRM контентом.
Подробную инструкцию по использованию CRM можно посмотреть по [ссылке](https://docs.strapi.io/dev-docs/quick-start)

Установите зависимости python коммандой
```sh
python3 -r requirements.txt
```

в папке `seller_crm` в файле `env` допишите селдующие переменные окружения:
```
STRAPI_TOKEN=токен, полученный в crm
TG_TOKEN=токен телеграм бота
REDIS_HOST=адрес хоста Redis
REDIS_PORT=порт Redis
```

## Запуск бота

Из корневой папки проекта запустить
```
python3 seller_bot.py
```