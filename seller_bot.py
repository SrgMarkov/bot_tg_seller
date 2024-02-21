import logging
import os

import redis
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    Updater,
    Filters,
)

from seller_bot_api import (
    add_product_to_cart,
    change_product_quantity,
    delete_product_from_cart,
    get_image_data,
    get_product_details,
    get_products_in_cart,
    get_or_create_cart,
    show_cart,
    post_email,
)
from seller_bot_keyboards import (
    get_cart_keyboard,
    get_products_keyboard,
    get_product_keyboard,
)

logger = logging.getLogger("telegram_bot_seller")


def start(update: Update, context: CallbackContext):
    context.user_data["chat_id"] = update.message.chat_id
    context.user_data["crm_connection"] = os.getenv('CRM_CONNECTION')
    update.message.reply_text(
        "Товары в наличии:",
        reply_markup=get_products_keyboard(
            context.user_data.get("request_headers"),
            context.user_data.get("crm_connection"),
        ),
    )
    return "HANDLE_MENU"


def get_product_info(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    request_headers = context.user_data.get("request_headers")
    context.user_data["product_id"] = query.data
    crm_connection = context.user_data.get("crm_connection")

    if query.data == "my_cart":
        cart_text, cart_buttons = show_cart(
            context.user_data.get("request_headers"),
            get_or_create_cart(
                str(query.message.from_user.id), request_headers, crm_connection
            ),
            crm_connection,
        )
        query.message.reply_text(
            cart_text, reply_markup=get_cart_keyboard(cart_buttons)
        )
        query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
        )
        return "CART"

    product = get_product_details(query.data, request_headers, crm_connection)
    query.bot.send_photo(
        photo=get_image_data(product, crm_connection),
        chat_id=context.user_data.get("chat_id"),
        caption=f"{product['title']} - {product['price']}р./килограмм \n\n {product['description']}",
        reply_markup=get_product_keyboard(),
    )
    query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
    )
    return "HANDLE_DESCRIPTION"


def get_back_product_list(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    request_headers = context.user_data.get("request_headers")
    crm_connection = context.user_data.get("crm_connection")

    if query.data == "back":
        query.message.reply_text(
            "Товары в наличии:",
            reply_markup=get_products_keyboard(request_headers, crm_connection),
        )
        query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
        )
        return "HANDLE_MENU"
    if query.data == "to_cart":
        if not context.user_data.get("cart_id"):
            context.user_data["cart_id"] = get_or_create_cart(
                str(query.message.from_user.id), request_headers, crm_connection
            )

        for product in get_products_in_cart(request_headers, crm_connection):
            quantity = product["attributes"]["quantity"] + 1
            if int(context.user_data.get("product_id")) == int(
                product["attributes"]["fish_shop"]["data"]["id"]
            ):
                change_product_quantity(
                    request_headers, product["id"], quantity, crm_connection
                )
                query.message.reply_text(
                    "Хотите заказать что то ещё?",
                    reply_markup=get_products_keyboard(request_headers, crm_connection),
                )
                query.bot.delete_message(
                chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
                )
                return "HANDLE_MENU"

        add_product_to_cart(
            int(context.user_data.get("product_id")),
            context.user_data.get("cart_id"),
            request_headers,
            crm_connection,
        )

        query.message.reply_text(
            "Хотите заказать что то ещё?",
            reply_markup=get_products_keyboard(request_headers, crm_connection),
        )
        query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
        )
        return "HANDLE_MENU"
    if query.data == "my_cart":
        cart_text, cart_buttons = show_cart(
            request_headers,
            get_or_create_cart(
                str(query.message.from_user.id), request_headers, crm_connection
            ),
            crm_connection,
        )
        query.message.reply_text(
            cart_text, reply_markup=get_cart_keyboard(cart_buttons)
        )
        query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
        )
        return "CART"


def handle_cart(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    request_headers = context.user_data.get("request_headers")
    crm_connection = context.user_data.get("crm_connection")
    if query.data == "back":
        query.message.reply_text(
            "Товары в наличии:",
            reply_markup=get_products_keyboard(request_headers, crm_connection),
        )
        query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
        )
        return "HANDLE_MENU"
    if query.data == "purchase":
        query.message.reply_text("Для оформления заказа пожалуйста введите свой email:")
        query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
        )
        return "WAITING_CONTACTS"
    try:
        delete_product_from_cart(query.data, request_headers, crm_connection)

        cart_text, cart_buttons = show_cart(
            request_headers,
            get_or_create_cart(
                str(query.message.from_user.id), request_headers, crm_connection
            ),
            crm_connection,
        )
        query.message.reply_text(
            cart_text, reply_markup=get_cart_keyboard(cart_buttons)
        )
        query.bot.delete_message(
        chat_id=context.user_data.get("chat_id"), message_id=query.message.message_id
        )
        return "CART"
    except Exception:
        return "CART"


def handle_email(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    request_headers = context.user_data.get("request_headers")
    crm_connection = context.user_data.get("crm_connection")

    post_email(username, user_input, user_id, request_headers, crm_connection)

    update.message.reply_text(f"{username}, ваш заказ оформлен")
    update.message.reply_text(
        "Желаете заказать что то еще?:",
        reply_markup=get_products_keyboard(request_headers, crm_connection),
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
