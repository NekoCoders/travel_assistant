import time
import traceback
from collections import defaultdict
from typing import List, Tuple

import telebot
from telebot import TeleBot
from telebot import types

from travel_assistant.common.custom_types import Product, ClientContext
from travel_assistant.consultant.assistant import Assistant

TOKEN = "7054321594:AAE5lT7J_wIL76aTwql1qzpSocnOriRPB50"


def start_listening_server(bot: TeleBot):
    print("Starting server...")
    bot.polling(none_stop=True, interval=0)


def format_products(products: List[Tuple[Product, str]]) -> str:
    message = "Вот что я нашел в каталоге RUSSPASS:\n\n"
    for p, reason in products:
        message += f"{p.title}\nhttps://russpass.ru/event/{p.id}\n{reason}\n\n"
    return message


if __name__ == "__main__":
    context_by_chat_id: dict[str, ClientContext] = defaultdict(ClientContext)
    options_by_chat_id: dict[str, List[str]] = defaultdict(List[str])
    bot = telebot.TeleBot(TOKEN, threaded=False)
    assistant = Assistant(verbose=True)

    def chat_with_assistant(chat_id, message_text, username):
        try:
            if message_text == "/start":
                text_to_send = "Здравствуйте, я Борис! Давайте я помогу вам подобрать досуг. Какие виды отдыха вам нравятся?"
                context = ClientContext(messages=[("ai", text_to_send)])
                options = assistant.get_options(context, "", "Какие виды отдыха вам нравятся?")
                context_by_chat_id[chat_id] = context
                options_by_chat_id[chat_id] = options

                markup = types.InlineKeyboardMarkup()
                for i, option in enumerate(options):
                    item = types.InlineKeyboardButton(option, callback_data=f"{i}")
                    markup.add(item)
                bot.send_message(chat_id, text_to_send, reply_markup=markup)
                print(f"Started chat with {username}")
            else:
                typing_cb = lambda: bot.send_chat_action(chat_id=chat_id, action='typing')
                old_context = context_by_chat_id[chat_id]
                (
                    new_context_by_chat_id,
                    bot_message, bot_question, options, products
                ) = assistant.chat_single(old_context, message_text, typing_cb=typing_cb)
                context_by_chat_id[chat_id] = new_context_by_chat_id
                options_by_chat_id[chat_id] = options

                bot.send_message(chat_id, bot_message)
                time.sleep(1)

                if products:
                    bot.send_message(chat_id, format_products(products))
                    time.sleep(1)

                if options:
                    markup = types.InlineKeyboardMarkup()
                    for i, option in enumerate(options):
                        item = types.InlineKeyboardButton(option, callback_data=f"{i}")
                        markup.add(item)
                    bot.send_message(chat_id, bot_question, reply_markup=markup)
                else:
                    bot.send_message(chat_id, bot_question)

                print(f"Got message from {username}, message: '{message_text}', answer: '{bot_message}'")
        except Exception as e:
            traceback.print_exc()

    @bot.message_handler(content_types=["text"])
    def answer_message(message):
        chat_with_assistant(message.chat.id, message.text, message.chat.username)

    @bot.callback_query_handler(func=lambda callback: True)
    def callback_button(call):
        if call.message:
            i = int(call.data)
            option = options_by_chat_id[call.message.chat.id][i]
            bot.answer_callback_query(call.id, show_alert=False)
            bot.send_message(call.message.chat.id, option)
            chat_with_assistant(call.message.chat.id, option, call.message.chat.username)


    start_listening_server(bot)
