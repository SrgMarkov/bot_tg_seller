# Телеграм бот - продажи

Скелет бота по продаже товаров через ТГ

## Как установить
Для работы бота и crm интернет магазина необходим Python версии не ниже 3.8, а так же [node.js](https://nodejs.org/en/) версии не ниже 18.16

Первым делом необходимо установить [strapi](https://github.com/strapi/strapi?tab=readme-ov-file), CRM для интернет магазина

```sh
npx create-strapi-app@latest seller_crm --quickstart
```

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

## Наполнение базы данных
Для корректной работы бота необходимо добавить в базу данных следующие сущности:
 - cart
 - cart-product
 - customer
 - fish-shop

Ниже описаны схемы создания сущностей

### Сущность cart

```
{
  "kind": "collectionType",
  "collectionName": "carts",
  "info": {
    "singularName": "cart",
    "pluralName": "carts",
    "displayName": "Cart",
    "description": ""
  },
  "options": {
    "draftAndPublish": true
  },
  "pluginOptions": {
    "i18n": {
      "localized": true
    }
  },
  "attributes": {
    "tg_id": {
      "pluginOptions": {
        "i18n": {
          "localized": true
        }
      },
      "type": "string"
    },
    "cart_products": {
      "type": "relation",
      "relation": "manyToMany",
      "target": "api::cart-product.cart-product",
      "mappedBy": "carts"
    },
    "customer": {
      "type": "relation",
      "relation": "manyToOne",
      "target": "api::customer.customer",
      "inversedBy": "carts"
    }
  }
}

```
### Сущность cart-product

```
{
  "kind": "collectionType",
  "collectionName": "cart_products",
  "info": {
    "singularName": "cart-product",
    "pluralName": "cart-products",
    "displayName": "Cart_products",
    "description": ""
  },
  "options": {
    "draftAndPublish": true
  },
  "pluginOptions": {},
  "attributes": {
    "fish_shop": {
      "type": "relation",
      "relation": "manyToOne",
      "target": "api::fish-shop.fish-shop",
      "inversedBy": "cart_products"
    },
    "carts": {
      "type": "relation",
      "relation": "manyToMany",
      "target": "api::cart.cart",
      "inversedBy": "cart_products"
    },
    "quantity": {
      "type": "integer"
    }
  }
}
```

### Сущность customer
```
{
  "kind": "collectionType",
  "collectionName": "customers",
  "info": {
    "singularName": "customer",
    "pluralName": "customers",
    "displayName": "customer",
    "description": ""
  },
  "options": {
    "draftAndPublish": true
  },
  "pluginOptions": {},
  "attributes": {
    "name": {
      "type": "string"
    },
    "email": {
      "type": "email"
    },
    "phone": {
      "type": "string"
    },
    "carts": {
      "type": "relation",
      "relation": "oneToMany",
      "target": "api::cart.cart",
      "mappedBy": "customer"
    },
    "tg_id": {
      "type": "string"
    }
  }
}
```

### Сущность fish-shop
```
{
  "kind": "collectionType",
  "collectionName": "fish_shops",
  "info": {
    "singularName": "fish-shop",
    "pluralName": "fish-shops",
    "displayName": "Products",
    "description": ""
  },
  "options": {
    "draftAndPublish": true
  },
  "pluginOptions": {},
  "attributes": {
    "title": {
      "type": "string"
    },
    "description": {
      "type": "text"
    },
    "picture": {
      "type": "media",
      "multiple": false,
      "required": false,
      "allowedTypes": [
        "images",
        "files",
        "videos",
        "audios"
      ]
    },
    "price": {
      "type": "decimal"
    },
    "cart_products": {
      "type": "relation",
      "relation": "oneToMany",
      "target": "api::cart-product.cart-product",
      "mappedBy": "fish_shop"
    }
  }
}

```

## Запуск бота

Из корневой папки проекта запустить
```
python3 seller_bot.py
```
