from io import BytesIO
import requests


def get_product_details(product_id, api_auth, crm_connection):
    payload = {"populate": "picture"}
    product_response = requests.get(
        f"http://{crm_connection}/api/fish-shops/{product_id}",
        headers=api_auth,
        params=payload,
        timeout=60,
    )
    product_response.raise_for_status()
    product_details = product_response.json()
    return product_details["data"]["attributes"]


def get_or_create_cart(user_id, api_auth, crm_connection):
    carts_response = requests.get(
        f"http://{crm_connection}/api/carts", headers=api_auth, timeout=60
    )
    carts_response.raise_for_status()
    for cart in carts_response.json()["data"]:
        if cart["attributes"]["tg_id"] == user_id:
            return cart["id"]
    payload = {"data": {"tg_id": user_id}}
    created_cart = requests.post(
        f"http://{crm_connection}/api/carts/",
        headers=api_auth,
        json=payload,
        timeout=60,
    )
    return created_cart.json()["data"]["id"]


def show_cart(api_auth, cart_id, crm_connection):
    payload = {"populate": "cart_products"}
    carts_response = requests.get(
        f"http://{crm_connection}/api/carts/{cart_id}",
        headers=api_auth,
        params=payload,
        timeout=60,
    )
    if carts_response.status_code == 404:
        return "В корзину пока не добавлено ни одного товара"

    cart_text = []
    cart_buttons = []
    summary_cost = 0
    for product in carts_response.json()["data"]["attributes"]["cart_products"]["data"]:
        product_id = product["id"]
        payload = {"populate": "fish_shop"}
        cart_products = requests.get(
            f"http://{crm_connection}/api/cart-products/{product_id}",
            headers=api_auth,
            params=payload,
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
            f"{product['title']}\nцена за кг. - {product['price']}р.\n{product_quantity}кг. в корзине за {round(product_position_cost, 2)}р.\n\n"
        )
    cart_text = (
        f"{''.join(cart_text)}\n Итоговая стоимость - {round(summary_cost, 2)}р."
    )
    return cart_text, cart_buttons


def get_image_data(product, crm_connection):
    picture_url = requests.get(
    f"http://{crm_connection}{product['picture']['data']['attributes']['formats']['medium']['url']}",
    timeout=60,
    )
    picture_url.raise_for_status()
    return BytesIO(picture_url.content)


def get_products_in_cart(api_token, crm_connection):
    payload = {"populate": "fish_shop"}
    products_in_cart = requests.get(
        f"http://{crm_connection}/api/cart-products",
        headers=api_token,
        params=payload,
        timeout=60,
    )
    products_in_cart.raise_for_status()
    return products_in_cart.json()["data"]


def change_product_quantity(api_token, product_id, quantity, crm_connection):
    payload = {"data": {"quantity": quantity}}
    requests.put(
        f"http://{crm_connection}/api/cart-products/{product_id}",
        json=payload,
        headers=api_token,
        timeout=60,
    )


def add_product_to_cart(product_id, cart_id, api_token, crm_connection):
    payload = {
            "data": {
                "quantity": 1,
                "fish_shop": {"connect": [product_id]},
                "carts": {"connect": [cart_id]},
            }
        }
    requests.post(
        f"http://{crm_connection}/api/cart-products/",
        headers=api_token,
        json=payload,
        timeout=60,
        )


def delete_product_from_cart(product, api_token, crm_connection):
    requests.delete(
    f"http://{crm_connection}/api/cart-products/{product}",
    headers=api_token,
    timeout=60,
)
