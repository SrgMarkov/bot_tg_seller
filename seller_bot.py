from io import BytesIO
import logging
import os

import redis
import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
)


def get_product_details(product_id, api_auth):
    product_response = requests.get(
        f"http://localhost:1337/api/fish-shops/{product_id}?populate=picture",
        headers=api_auth,
        timeout=60,
    )
    product_response.raise_for_status()
    product_details = product_response.json()
    return product_details["data"]["attributes"]


def get_products_keyboard(api_auth):
    products_response = requests.get(
        "http://localhost:1337/api/fish-shops/",
        headers=api_auth,
        timeout=60,
    )
    products_response.raise_for_status()
    keyboard = [
        [
            InlineKeyboardButton(
                product["attributes"]["title"], callback_data=int(product["id"])
            )
        ]
        for product in products_response.json()["data"]
    ]
    keyboard.append([InlineKeyboardButton("Моя корзина", callback_data="my_cart")])
    return InlineKeyboardMarkup(keyboard)


def get_or_create_cart(user_id, api_auth):
    carts_response = requests.get(
        "http://localhost:1337/api/carts", headers=api_auth, timeout=60
    )
    carts_response.raise_for_status()
    for cart in carts_response.json()["data"]:
        if cart["attributes"]["tg_id"] == user_id:
            return cart["id"]
    payload = {"data": {"tg_id": user_id}}
    created_cart = requests.post(
        "http://localhost:1337/api/carts/", headers=api_auth, json=payload, timeout=60
    )
    return created_cart.json()["data"]["id"]


def show_cart(api_auth, cart_id):
    carts_response = requests.get(
        f"http://localhost:1337/api/carts/{cart_id}?populate=cart_products",
        headers=api_auth,
        timeout=60,
    )
    if carts_response.status_code == 404:
        return "В корзину пока не добавлено ни одного товара"

    cart_text = []
    cart_buttons = []
    summary_cost = 0
    for product in carts_response.json()["data"]["attributes"]["cart_products"]["data"]:
        product_id = product['id']
        cart_products = requests.get(
            f"http://localhost:1337/api/cart-products/{product_id}?populate=fish_shop",
            headers=api_auth,
            timeout=60,
        )
        cart_products.raise_for_status()
        product_in_cart = cart_products.json()["data"]["attributes"]
        product_quantity = product_in_cart["quantity"]
        product = product_in_cart["fish_shop"]["data"]["attributes"]
        product_position_cost = product_quantity * product["price"]
        summary_cost += product_position_cost
        cart_buttons.append((product["title"], product_id))
        cart_text.append(
            f"{product['title']}\nцена за кг. - {product['price']}р.\n{product_quantity}кг. в корзине за {product_position_cost}р.\n\n"
        )
    cart_text = (
        f"{''.join(cart_text)}\n Итоговая стоимость - {round(summary_cost, 2)}р."
    )
    return cart_text, cart_buttons


def get_cart_keyboard(buttons):
    cart_keyboard = [
        [InlineKeyboardButton(f"удалить {button}", callback_data=number)]
        for button, number in buttons
    ]
    cart_keyboard.append([InlineKeyboardButton("Оформить заказ", callback_data="purchase")])
    cart_keyboard.append([InlineKeyboardButton("В меню", callback_data="back")])
    return InlineKeyboardMarkup(cart_keyboard)


def start(update: Update, context: CallbackContext):
    context.user_data["chat_id"] = update.message.chat_id
    update.message.reply_text(
        "Товары в наличии:",
        reply_markup=get_products_keyboard(context.user_data.get("request_headers")),
    )
    return "HANDLE_MENU"


def get_product_info(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    request_headers = context.user_data.get("request_headers")
    context.user_data["product_id"] = query.data
    if query.data == "my_cart":
        cart_text, cart_buttons = show_cart(
            context.user_data.get("request_headers"),
            get_or_create_cart(str(query.message.from_user.id), request_headers),
        )
        query.message.reply_text(
            cart_text, reply_markup=get_cart_keyboard(cart_buttons)
        )
        return "CART"

    product = get_product_details(query.data, request_headers)
    picture_url = requests.get(
        f"http://localhost:1337{product['picture']['data']['attributes']['formats']['medium']['url']}",
        timeout=60,
    )
    picture_url.raise_for_status()
    image_data = BytesIO(picture_url.content)

    query.bot.deleteMessage(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")],
        [InlineKeyboardButton("Добавить в корзину", callback_data="to_cart")],
        [InlineKeyboardButton("Моя корзина", callback_data="my_cart")],
    ]
    query.bot.send_photo(
        photo=image_data,
        chat_id=context.user_data.get("chat_id"),
        caption=f"{product['title']} - {product['price']}р./килограмм \n\n {product['description']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return "HANDLE_DESCRIPTION"


def get_back_product_list(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    request_headers = context.user_data.get("request_headers")
    if query.data == "back":
        query.message.reply_text(
            "Товары в наличии:", reply_markup=get_products_keyboard(request_headers)
        )
        return "HANDLE_MENU"
    if query.data == "to_cart":
        if not context.user_data.get("cart_id"):
            context.user_data["cart_id"] = get_or_create_cart(
                str(query.message.from_user.id), request_headers
            )
        products_in_cart = requests.get(
            "http://localhost:1337/api/cart-products?populate=fish_shop",
            headers=request_headers,
            timeout=60,
        )
        products = products_in_cart.json()["data"]
        for product in products:
            quantity = product["attributes"]["quantity"] + 1
            if int(context.user_data.get("product_id")) == int(
                product["attributes"]["fish_shop"]["data"]["id"]
            ):
                payload = {"data": {"quantity": quantity}}
                requests.put(
                    f"http://localhost:1337/api/cart-products/{product['id']}",
                    json=payload,
                    headers=request_headers,
                    timeout=60,
                )
                query.message.reply_text(
                    "Хотите заказать что то ещё?",
                    reply_markup=get_products_keyboard(request_headers),
                )
                return "HANDLE_MENU"

        payload = {
            "data": {
                "quantity": 1,
                "fish_shop": {"connect": [int(context.user_data.get("product_id"))]},
                "carts": {"connect": [context.user_data.get("cart_id")]},
            }
        }
        requests.post(
            "http://localhost:1337/api/cart-products/",
            headers=request_headers,
            json=payload,
            timeout=60,
        )

        query.message.reply_text(
            "Хотите заказать что то ещё?",
            reply_markup=get_products_keyboard(request_headers),
        )
        return "HANDLE_MENU"
    if query.data == "my_cart":
        cart_text, cart_buttons = show_cart(
            request_headers,
            get_or_create_cart(str(query.message.from_user.id), request_headers),
        )
        query.message.reply_text(
            cart_text, reply_markup=get_cart_keyboard(cart_buttons)
        )
        return "CART"


def handle_cart(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    request_headers = context.user_data.get("request_headers")
    if query.data == "back":
        query.message.reply_text(
            "Товары в наличии:", reply_markup=get_products_keyboard(request_headers)
        )
        return "HANDLE_MENU"
    if query.data == "purchase":
        query.message.reply_text("Для оформления заказа пожалуйста введите свой email:")
        return "WAITING_CONTACTS"
    try:
        requests.delete(
            f"http://localhost:1337/api/cart-products/{query.data}",
            headers=request_headers,
            timeout=60,
        )
        cart_text, cart_buttons = show_cart(
            request_headers,
            get_or_create_cart(str(query.message.from_user.id), request_headers),
        )
        query.message.reply_text(
            cart_text, reply_markup=get_cart_keyboard(cart_buttons)
        )
        return "CART"
    except Exception:
        return "CART"


def handle_email(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    request_headers = context.user_data.get("request_headers")

    payload = {"data": {"username": username, 
                        "email": user_input,
                        "tg_id":str(user_id),
                        }}

    created_cart = requests.post(
        "http://localhost:1337/api/customers/", 
        headers=request_headers,
        json=payload,
        timeout=60
    )
    update.message.reply_text(f"{username}, ваш заказ оформлен")
    update.message.reply_text(
            "Желаете заказать что то еще?:", reply_markup=get_products_keyboard(request_headers)
        )
    return "HANDLE_MENU"

def handle_users_reply(update: Update, context: CallbackContext):
    if not context.user_data.get("redis_connection"):
        context.user_data["redis_connection"] = redis.Redis(
            host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT"))
        )
    if not context.user_data.get("request_headers"):
        context.user_data["request_headers"] = {
            "Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}"
        }

    db = context.user_data["redis_connection"]
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == "/start":
        user_state = "START"
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        "START": start,
        "HANDLE_MENU": get_product_info,
        "HANDLE_DESCRIPTION": get_back_product_list,
        "CART": handle_cart,
        "WAITING_CONTACTS": handle_email,
    }
    state_handler = states_functions[user_state]

    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


if __name__ == "__main__":
    dotenv_path = os.path.join("seller_crm", ".env")
    load_dotenv(dotenv_path)
    updater = Updater(os.getenv("TG_TOKEN"))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", handle_users_reply))
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))

    updater.start_polling()
    updater.idle()
