import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_products_keyboard(api_auth, crm_connection):
    products_response = requests.get(
        f"http://{crm_connection}/api/fish-shops/",
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


def get_cart_keyboard(buttons):
    cart_keyboard = [
        [InlineKeyboardButton(f"удалить {button}", callback_data=number)]
        for button, number in buttons
    ]
    cart_keyboard.append(
        [InlineKeyboardButton("Оформить заказ", callback_data="purchase")]
    )
    cart_keyboard.append([InlineKeyboardButton("В меню", callback_data="back")])
    return InlineKeyboardMarkup(cart_keyboard)


def get_product_keyboard():
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")],
        [InlineKeyboardButton("Добавить в корзину", callback_data="to_cart")],
        [InlineKeyboardButton("Моя корзина", callback_data="my_cart")],
    ]
    return InlineKeyboardMarkup(keyboard)
