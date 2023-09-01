import random
import sqlite3
from datetime import datetime

import requests
import telebot
from telebot import types

from my_token import TOKEN, admin_id

# Главное меню с кнопками
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения текущего состояния каждого пользователя
user_states = {}

# Константы для состояний перехода выбора блюд
SELECT_DISH, SELECT_GRAMS, SELECT_PAYMENT, SELECT_ADDRESS, VIEW_HISTORY, DEL_HISTORY, SEND_HISTORY = range(7)
# В начале кода, определите состояния для админ команды изменение блюд
WAITING_FOR_DISH_NAME_CHANGE = 10
WAITING_FOR_NEW_DISH_NAME = 11
list_dish = []


# список название блюд
def get_dishes():
    global list_dish
    conn = sqlite3.connect("data_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM dishes")
    list_dish = [row[0] for row in cursor.fetchall()]
    conn.close()
    return list_dish


get_dishes()
old_name = ''
# Создаем клавиатуру меню блюд с тремя колонками
dishes_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
# Функция для обновления клавиатуры с блюдами
def update_dishes_menu():
    global list_dish, dishes_menu
    dishes_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for dish in list_dish:
        dishes_menu.add(types.KeyboardButton(dish))
# Перебираем список блюд и добавляем каждое блюдо как кнопку в меню
for dish in list_dish:
    dishes_menu.add(types.KeyboardButton(dish))
# список размеров порций
list_size = ["маленькая", "средняя", "большая", ]
# Кнопки меню размер порций
grams_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
grams_menu.add(types.KeyboardButton("маленькая"))
grams_menu.add(types.KeyboardButton("средняя"))
grams_menu.add(types.KeyboardButton("большая"))

# Меню оплаты
payment_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
payment_menu.add(types.KeyboardButton("Наличные"))
payment_menu.add(types.KeyboardButton("Картой"))
# Удаление заказа
del_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
del_menu.add(types.KeyboardButton("Обнулить заказ"))
del_menu.add(types.KeyboardButton('Подтвердить '))

# Глобальная переменная для отслеживания этапа
current_step = None


# Ожидание команды /change_menu
@bot.message_handler(commands=['change_menu'])
def handle_change_menu(message):
    global current_step
    user_id = message.from_user.id
    if user_id == admin_id:
        current_step = "waiting_for_dish_name"
        bot.send_message(message.chat.id, "Сначала введите название блюда, которое хотите изменить")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде")


# Обработчик для ожидания названия блюда
@bot.message_handler(func=lambda message: current_step == "waiting_for_dish_name")
def handle_waiting_for_dish_name(message):
    global current_step, old_name
    dish_name = message.text
    if dish_name in list_dish:
        old_name = dish_name
        current_step = "waiting_for_new_dish_name"
        bot.send_message(message.chat.id, f"Вы выбрали блюдо '{dish_name}'. Теперь введите новое название.")
    else:
        bot.send_message(message.chat.id, f"Блюдо '{dish_name}' не найдено в меню. Попробуйте ещё раз.")


# Обработчик для изменения названия блюда
@bot.message_handler(func=lambda message: current_step == "waiting_for_new_dish_name")
def handle_change_dish_name(message):
    global current_step, old_name
    new_dish_name = message.text
    index = list_dish.index(old_name)
    list_dish[index] = new_dish_name
    bot.send_message(message.chat.id, f"Блюдо успешно изменено на '{new_dish_name}'.")
    current_step = None  # Сбрасываем этап обработки
    conn = sqlite3.connect("data_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE dishes SET name = ? WHERE name = ?", (new_dish_name, old_name))
    conn.commit()
    conn.close()
    update_dishes_menu()




@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id

    # Проверяем, есть ли уже запись для этого пользователя в user_states
    if user_id not in user_states:
        # Если нет, создаем новую запись
        user_states[user_id] = {
            'state': SELECT_DISH,
            'dish': None,
            'grams': None,
            'payment': None,
            'order_history': []
        }

    # Отправляем приветственное сообщение
    bot.send_message(message.chat.id, "Добро пожаловать! Пожалуйста выберите блюдо:", reply_markup=dishes_menu)


# Обработчик выбора блюда
@bot.message_handler(func=lambda message: message.text in list_dish and user_states.get(message.from_user.id, {}).get(
    'state') == SELECT_DISH)
def handle_dish_selection(message):
    user_id = message.from_user.id
    user_state = user_states.get(user_id)
    user_state['dish'] = message.text
    user_state['state'] = SELECT_GRAMS
    user_state['order_history'].append(f'Выбраное блюдо: {message.text}')
    bot.send_message(message.chat.id, "Пожалуйста выберите размер порции:", reply_markup=grams_menu)


# Обработчик выбора граммовки
@bot.message_handler(func=lambda message: message.text in list_size)
def handle_grams_selection(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]
    user_state['grams'] = message.text
    user_state['state'] = SELECT_ADDRESS
    user_state['order_history'].append(f'Выбраная порция: {message.text}')
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Введите ваш адрес для доставки?", reply_markup=markup)


# Обработчки записи адреса
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('state') == SELECT_ADDRESS)
def handle_address_input(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]
    user_state['address'] = message.text  # Запоминаем адрес
    user_state['state'] = SELECT_PAYMENT
    user_state['order_history'].append(f'Ваш адресс: {message.text}')

    bot.send_message(message.chat.id, "Выберите способ оплаты:", reply_markup=payment_menu)


def send_message(order_history_text, user_username, order_number):
    # Создаем сообщение о заказе с датой, номером заказа, историей заказа и именем пользователя
    message_text = f"Дата заказа: {datetime.now().strftime('%Y-%m-%d')}\n"
    message_text += f"Номер заказа: #{order_number}\n"
    message_text += f"Имя пользователя: {user_username}\n"
    message_text += f"История заказа:\n{order_history_text}"

    # Создаем JSON-словарь с данными
    message_data = {
        "chat_id": 1052866868,  # ID пользователя, которому отправляем сообщение
        "text": message_text,
        "parse_mode": "Markdown",  # Вы можете выбрать форматирование текста (по желанию)
    }

    # Отправляем POST-запрос
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    response = requests.post(url, json=message_data)

    response.json()


# Обработчик выбора оплаты
@bot.message_handler(func=lambda message: message.text in ["Наличные", "Картой"])
def handle_payment_selection(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]
    user_state['payment'] = message.text
    user_state['state'] = DEL_HISTORY
    user_state['order_history'].append(f'Способ оплаты: {message.text}')
    # Генерируем историю заказа
    order_history = user_state['order_history']
    order_history_text = "\n".join(order_history)
    bot.send_message(message.chat.id,
                     f"Ваш заказ:\n{order_history_text}\nПодтвердите если заказ верен или измените его",
                     reply_markup=del_menu)


# Обработчик обнуление заказа
@bot.message_handler(func=lambda message: message.text in ['Обнулить заказ', 'Подтвердить'])
def del_history_order(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]
    user_id = message.from_user.id
    # получаем имя от пользователя
    user_username = message.from_user.first_name

    # Сбрасываем историю заказа для данного пользователя
    if message.text == 'Обнулить заказ':
        if user_id in user_states:
            user_states[user_id]['order_history'] = []
        bot.send_message(message.chat.id, "История заказа обнулена. Пожалуйста, заполните новый заказ:",
                         reply_markup=dishes_menu)
        # Предложение выбрать блюдо и установка состояния SELECT_DISH
        user_states[user_id]['state'] = SELECT_DISH

    if message.text == 'Подтвердить':
        # Генерируем историю заказа
        order_history = user_state['order_history']
        order_history_text = "\n".join(order_history)
        bot.send_message(message.chat.id, "Заказ подтверждён и отправлен,хотите сделать новый заказ?:",
                         reply_markup=dishes_menu)
        # Генерируем номер заказа (это может быть, например, случайное число)
        order_number = random.randint(1000, 9999)
        # Отправляем сообщение о заказе
        send_message(order_history_text, user_username, order_number)
        user_states[user_id]['order_history'] = []
        user_state['state'] = SELECT_DISH


# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
