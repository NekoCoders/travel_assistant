import time
from collections import defaultdict
from typing import List

import telebot
from telebot import TeleBot
from telebot import types

from travel_assistant.common.custom_types import Product
from travel_assistant.consultant.assistant import Assistant

TOKEN = "7054321594:AAE5lT7J_wIL76aTwql1qzpSocnOriRPB50"


def start_listening_server(bot: TeleBot):
    print("Starting server...")
    bot.polling(none_stop=True, interval=0)


def format_products(products: List[Product]) -> str:
    message = ""
    for p in products:
        message += f"{p.title}: https://russpass.ru/event/{p.id}\n"
    return message


if __name__ == "__main__":
    context_by_chat_id: dict[str, list] = defaultdict(list)
    bot = telebot.TeleBot(TOKEN, threaded=False)
    assistant = Assistant(verbose=True)

    @bot.message_handler(content_types=["text"])
    def answer_message(message):
        try:
            if message.text == "/start":
                context_by_chat_id[message.chat.id] = []
                text_to_send = "Здравствуйте, я Борис! Давайте я помогу вам подобрать досуг. Что Вас интересует?"
                bot.send_message(message.chat.id, text_to_send)
            else:
                old_context = context_by_chat_id[message.chat.id]
                new_context_by_chat_id, bot_response, bot_question, options, products = assistant.chat_single(old_context, message.text)
                text_to_send = bot_response
                bot.send_message(message.chat.id, bot_response)
                time.sleep(1)
                if products:
                    bot.send_message(message.chat.id, format_products(products))
                    time.sleep(1)

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for option in options:
                    item = types.KeyboardButton(option)
                    markup.add(item)
                bot.send_message(message.chat.id, bot_question, reply_markup=markup)

                context_by_chat_id[message.chat.id] = new_context_by_chat_id

            print(f"Got message from {message.chat.username}, message: '{message.text}', answer: '{text_to_send}'")
        except Exception as e:
            print(e)

    # обработка нажатий кнопок
    # @bot.callback_query_handler(func=lambda call: True)
    # def callback_keys_worker(call):
    #     bot.send_message(
    #         call.message.chat.id,
    #         f"Здравствуйте, я Борис! Давайте я помогу вам подобрать досуг. Что Вас интересует?",
    #     )

    start_listening_server(bot)
