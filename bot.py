import telebot
import json
import random
import os
from telebot import types

TOKEN = '8930682539:AAG9gM0GOinwPXoBeO5R_Wkg76NNSE8s4Oo'
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'music.json'
LIKES_FILE = 'likes.json'
DISLIKES_FILE = 'dislikes.json'

def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения {filename}: {e}")

music_db = load_json(DATA_FILE, [])
likes_db = load_json(LIKES_FILE, {})
dislikes_db = load_json(DISLIKES_FILE, {})

def get_wave_keyboard(track_index):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_like = types.InlineKeyboardButton("❤️", callback_data=f"like_{track_index}")
    btn_dislike = types.InlineKeyboardButton("👎", callback_data=f"dislike_{track_index}")
    btn_next = types.InlineKeyboardButton("⏭ Дальше", callback_data="next_wave")
    markup.add(btn_like, btn_dislike)
    markup.add(btn_next)
    return markup

def get_like_keyboard(track_index):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❤️ Мне нравится", callback_data=f"like_{track_index}"))
    return markup

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎧 Моя волна", "❤️ Любимые", "🔍 Искать музыку", "➕ Добавить музыку")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Выбери действие:", reply_markup=get_main_menu())

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    file_id = None
    title = "Неизвестный трек"
    performer = "Неизвестный исполнитель"

    if message.content_type == 'audio' and message.audio:
        file_id = message.audio.file_id
        title = message.audio.title or "Без названия"
        performer = message.audio.performer or "Неизвестный"
    elif message.content_type == 'document' and message.document:
        if message.document.file_name and message.document.file_name.lower().endswith('.mp3'):
            file_id = message.document.file_id
            title = message.document.file_name.rsplit('.', 1)[0]
            performer = "Файл"
        else:
            bot.send_message(message.chat.id, "Отправь аудио в формате MP3.")
            return

    if file_id:
        music_db.append({"id": file_id, "title": f"{performer} - {title}"})
        save_json(DATA_FILE, music_db)
        bot.send_message(message.chat.id, f"✅ Добавлен: {performer} - {title}")

def send_wave_track(chat_id, user_id):
    if not music_db:
        bot.send_message(chat_id, "База пуста! Сначала добавь музыку (перешли песню в чат).")
        return
    user_dislikes = dislikes_db.get(str(user_id), [])
    available = [i for i in range(len(music_db)) if i not in user_dislikes]
    if not available:
        bot.send_message(chat_id, "Все треки в дизлайках!")
        return
    idx = random.choice(available)
    bot.send_audio(chat_id, music_db[idx]['id'], reply_markup=get_wave_keyboard(idx))

@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text
    user_id = str(message.from_user.id)

    if text == "🎧 Моя волна":
        send_wave_track(message.chat.id, user_id)
    elif text == "❤️ Любимые":
        user_likes = likes_db.get(user_id, [])
        if not user_likes:
            bot.send_message(message.chat.id, "У тебя пока нет любимых треков 💔")
            return
        valid_likes = [i for i in user_likes if i < len(music_db)]
        if not valid_likes:
            bot.send_message(message.chat.id, "Любимые треки не найдены в базе.")
            return
        idx = random.choice(valid_likes)
        bot.send_audio(message.chat.id, music_db[idx]['id'], reply_markup=get_like_keyboard(idx))
    elif text == "➕ Добавить музыку":
        bot.send_message(message.chat.id, "Отправь или перешли сюда MP3-файл.")
    elif text == "🔍 Искать музыку":
        bot.send_message(message.chat.id, "Напиши название песни или исполнителя прямо в чат.")
    else:
        query = text.lower()
        results = [i for i, t in enumerate(music_db) if query in t['title'].lower()]
        if not results:
            bot.send_message(message.chat.id, "Ничего не найдено 😔")
            return
        bot.send_message(message.chat.id, f"🔎 Найдено {len(results)}:")
        for i in results[:5]:
            bot.send_audio(message.chat.id, music_db[i]['id'], reply_markup=get_like_keyboard(i))

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    
    if call.data.startswith('like_'):
        idx = int(call.data.split('_')[1])
        if user_id not in likes_db:
            likes_db[user_id] = []
        if idx not in likes_db[user_id]:
            likes_db[user_id].append(idx)
            save_json(LIKES_FILE, likes_db)
            bot.answer_callback_query(call.id, "❤️ В любимых!")
        else:
            bot.answer_callback_query(call.id, "Уже в любимых!")
    elif call.data.startswith('dislike_'):
        idx = int(call.data.split('_')[1])
        if user_id not in dislikes_db:
            dislikes_db[user_id] = []
        if idx not in dislikes_db[user_id]:
            dislikes_db[user_id].append(idx)
            save_json(DISLIKES_FILE, dislikes_db)
        bot.answer_callback_query(call.id, "👎 Пропускаю")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        send_wave_track(chat_id, user_id)
    elif call.data == "next_wave":
        bot.answer_callback_query(call.id, "Следующий ⏭")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        send_wave_track(chat_id, user_id)

print("Бот готов к работе!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
