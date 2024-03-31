from collections import defaultdict

import telebot
from telebot import TeleBot

TOKEN = "7054321594:AAE5lT7J_wIL76aTwql1qzpSocnOriRPB50"


def start_listening_server(bot: TeleBot):
    print("Starting server...")
    bot.polling(none_stop=True, interval=0)


if __name__ == "__main__":
    context_by_chat_id: dict[str, list] = defaultdict(list)
    bot = telebot.TeleBot(TOKEN, threaded=False)

    @bot.message_handler(content_types=["text"])
    def answer_message(message):
        try:
            if message.text == "/start":
                context_by_chat_id[message.chat.id] = []
                text_to_send = "Здравствуйте, я Борис! Давайте я помогу вам подобрать досуг. Что Вас интересует?"
            else:
                # text_to_send, new_context_by_chat_id = get_message_and_new_context(message.text, old_context)
                text_to_send = "123"
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
