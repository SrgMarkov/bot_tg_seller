import logging
import os

import redis
import requests
from dotenv import load_dotenv
from io import BytesIO
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
