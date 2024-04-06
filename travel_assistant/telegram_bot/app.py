from collections import defaultdict

import telebot
from telebot import TeleBot

from travel_assistant.consultant.assistant import Assistant

TOKEN = "7054321594:AAE5lT7J_wIL76aTwql1qzpSocnOriRPB50"


def start_listening_server(bot: TeleBot):
    print("Starting server...")
    bot.polling(none_stop=True, interval=0)


if __name__ == "__main__":
    context_by_chat_id: dict[str, list] = defaultdict(list)
    bot = telebot.TeleBot(TOKEN, threaded=False)
    assistant = Assistant()

    @bot.message_handler(content_types=["text"])
    def answer_message(message):
        try:
            if message.text == "/start":
                context_by_chat_id[message.chat.id] = []
                text_to_send = "Здравствуйте, я Борис! Давайте я помогу вам подобрать досуг. Что Вас интересует?"
            else:
                old_context = context_by_chat_id[message.chat.id]
                new_context_by_chat_id, text_to_send, options = assistant.chat_single(old_context, message.text)
                text_to_send = f"{text_to_send}\n{options}"
                context_by_chat_id[message.chat.id] = new_context_by_chat_id
            bot.send_message(
                message.chat.id, text_to_send,
            )
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
