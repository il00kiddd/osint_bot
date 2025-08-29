import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from deepface import DeepFace
import os, uuid, datetime

TOKEN = "8271414144:AAF7d5OiCipvFXRqDSZcVurJa5FsCO57EYE"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ===== Главное меню =====
def main_menu_inline():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📱 Телефон", callback_data="phone"),
        InlineKeyboardButton("✉️ Email", callback_data="email"),
        InlineKeyboardButton("🔎 Никнейм/Соцсети", callback_data="nickname"),
        InlineKeyboardButton("📷 Поиск по лицу", callback_data="face")
    )
    return markup

@bot.message_handler(commands=['start'])
def start_msg(message):
    bot.send_message(message.chat.id,
                     "👋 Привет! Я <b>Илюшка Локальный</b> — твой OSINT бот.\nВыбери поиск:",
                     reply_markup=main_menu_inline())

# ===== Локальный поиск никнеймов =====
def nickname_lookup(username):
    sites = {
        "GitHub": ("https://github.com/", "icons/github.png"),
        "Twitter": ("https://x.com/", "icons/twitter.png"),
        "Instagram": ("https://www.instagram.com/", "icons/instagram.png"),
        "TikTok": ("https://www.tiktok.com/@", "icons/tiktok.png"),
        "Reddit": ("https://www.reddit.com/user/", "icons/reddit.png")
    }
    results = []
    for name, (url, icon) in sites.items():
        results.append((name, url + username, icon))
    return results

# ===== Сохранение новых фото =====
def save_new_face(file_content, username="user"):
    folder = "faces_db_new"
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = f"{folder}/{username}_{uuid.uuid4()}.jpg"
    with open(filename, "wb") as f:
        f.write(file_content)
    return filename

# ===== Поиск лиц =====
def face_lookup(file_path):
    face_dirs = ["faces_db1", "faces_db2", "faces_db_new"]
    matches = []
    for faces_folder in face_dirs:
        if not os.path.exists(faces_folder):
            continue
        for f in os.listdir(faces_folder):
            if f.lower().endswith((".jpg", ".png")):
                path = os.path.join(faces_folder, f)
                try:
                    result = DeepFace.verify(file_path, path, enforce_detection=False)
                    if result["distance"] < 0.4:
                        matches.append((os.path.splitext(f)[0], result["distance"]))
                except:
                    continue
    matches = sorted(matches, key=lambda x: x[1])
    if matches:
        return [f"✅ {name} (точность {1-dist:.2f})" for name, dist in matches]
    return None

# ===== HTML отчёт =====
def generate_html_report(query, results_dict):
    if not any(results_dict.values()):
        return None
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = f"report_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.html"
    html = f"""
    <html><head><meta charset='utf-8'><title>OSINT Report</title>
    <style>
    body {{ font-family: Arial; background:#f4f4f9; }}
    h1 {{ color:#2c3e50; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align:left; }}
    th {{ background-color: #3498db; color:white; }}
    tr:nth-child(even) {{ background-color:#f2f2f2; }}
    a {{ text-decoration:none; color:#2980b9; }}
    img.icon {{ width:16px; vertical-align:middle; }}
    </style></head><body>
    <h1>OSINT Report: {query}</h1><p>Дата: {now}</p>
    """
    for section, items in results_dict.items():
        if not items:
            continue
        html += f"<h2>{section}</h2><table><tr><th>Результат</th></tr>"
        for item in items:
            if isinstance(item, tuple):
                name, url, icon = item
                html += f"<tr><td><img class='icon' src='{icon}'> <a href='{url}' target='_blank'>{name}</a></td></tr>"
            else:
                html += f"<tr><td>{item}</td></tr>"
        html += "</table>"
    html += "</body></html>"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename

# ===== Callback меню =====
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "phone":
        msg = bot.send_message(call.message.chat.id, "Введите номер телефона (локальная версия не проверяет):")
        bot.register_next_step_handler(msg, lambda m: search_placeholder(m, "Телефон"))
    elif call.data == "email":
        msg = bot.send_message(call.message.chat.id, "Введите email (локальная версия не проверяет):")
        bot.register_next_step_handler(msg, lambda m: search_placeholder(m, "Email"))
    elif call.data == "nickname":
        msg = bot.send_message(call.message.chat.id, "Введите никнейм:")
        bot.register_next_step_handler(msg, lambda m: search_nickname(m))
    elif call.data == "face":
        msg = bot.send_message(call.message.chat.id, "Отправь фото для поиска лица:")
        bot.register_next_step_handler(msg, lambda m: search_face(m))

# ===== Обработчики поиска =====
def search_placeholder(message, label):
    results_dict = {label: [f"🔹 {message.text} (локальный поиск не активен)"]}
    filename = generate_html_report(message.text.strip(), results_dict)
    bot.send_document(message.chat.id, open(filename, "rb"))

def search_nickname(message):
    results_dict = {"Никнеймы": nickname_lookup(message.text.strip())}
    filename = generate_html_report(message.text.strip(), results_dict)
    bot.send_document(message.chat.id, open(filename, "rb"))

def search_face(message):
    if message.content_type == "photo":
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        save_new_face(downloaded_file)
        filename = f"tmp_{uuid.uuid4()}.jpg"
        with open(filename, 'wb') as f:
            f.write(downloaded_file)
        results = face_lookup(filename)
        os.remove(filename)
        results_dict = {"Лицо": results} if results else {}
        filename = generate_html_report("Лицо", results_dict)
        if filename:
            bot.send_document(message.chat.id, open(filename, "rb"))
        else:
            bot.send_message(message.chat.id, "❌ Данных для отчёта не найдено.")
    else:
        bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте фото")

# ===== Запуск бота =====
print("🤖 Локальный OSINT бот Илюшка с графическим меню запущен...")
bot.polling(none_stop=True)
