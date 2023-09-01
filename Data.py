import sqlite3

conn = sqlite3.connect('data_bot.db')
cursor = conn.cursor()
list_dish = ['Блюдо 1', 'Блюдо 2', 'Блюдо 3', 'Блюдо 4', 'Блюдо 5', 'Блюдо 6']
# Создаем таблицу для хранения данных
cursor.execute('''CREATE TABLE IF NOT EXISTS dishes (id INTEGER PRIMARY KEY, name TEXT)''')
# Добавляем начальные данные (если их нет)
for dish in list_dish:
    cursor.execute("INSERT INTO dishes (name) VALUES (?)", (dish,))

conn.commit()
conn.close()