import time
from collections import defaultdict
from typing import List

import telebot
from telebot import TeleBot
from telebot import types

from travel_assistant.common.custom_types import Product, ClientContext
from travel_assistant.consultant.assistant import Assistant

TOKEN = "7054321594:AAE5lT7J_wIL76aTwql1qzpSocnOriRPB50"


def start_listening_server(bot: TeleBot):
    print("Starting server...")
    bot.polling(none_stop=True, interval=0)


def format_products(products: List[Product]) -> str:
    message = "Вот что я нашел в каталоге RUSSPASS:\n\n"
    for p in products:
        message += f"{p.title}\nhttps://russpass.ru/event/{p.id}\n\n"
    return message


if __name__ == "__main__":
    context_by_chat_id: dict[str, ClientContext] = defaultdict(ClientContext)
    bot = telebot.TeleBot(TOKEN, threaded=False)
    assistant = Assistant(verbose=True)

    @bot.message_handler(content_types=["text"])
    def answer_message(message):
        try:
            if message.text == "/start":
                context_by_chat_id[message.chat.id] = ClientContext()
                text_to_send = "Здравствуйте, я Борис! Давайте я помогу вам подобрать досуг. Что Вас интересует?"
                bot.send_message(message.chat.id, text_to_send)
                print(f"Started chat with {message.chat.username}")
            else:
                old_context = context_by_chat_id[message.chat.id]
                new_context_by_chat_id, bot_message, bot_question, options, products = assistant.chat_single(old_context, message.text)

                bot.send_message(message.chat.id, bot_message)
                time.sleep(1)

                if products:
                    bot.send_message(message.chat.id, format_products(products))
                    time.sleep(1)

                if options:
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    for option in options:
                        item = types.KeyboardButton(option)
                        markup.add(item)
                    bot.send_message(message.chat.id, bot_question, reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, bot_question)

                context_by_chat_id[message.chat.id] = new_context_by_chat_id

                print(f"Got message from {message.chat.username}, message: '{message.text}', answer: '{bot_message}'")
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
