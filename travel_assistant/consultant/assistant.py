from __future__ import annotations

import json
from typing import List, Tuple, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models.gigachat import GigaChat
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, tool

from travel_assistant.common.custom_types import Product, ClientContext
from travel_assistant.common.gigachat_api import AUTH_DATA
from travel_assistant.consultant.agent_utils import create_agent
from travel_assistant.consultant.assistant_prompts import system_ask, human_ask, system_options, \
    human_options, bot_ask, bot_options, system_interests, bot_interests, human_interests, system_reason, bot_reason, \
    human_reason
from travel_assistant.database.database import ProductDatabase


class Assistant:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.llm = GigaChat(model="GigaChat", credentials=AUTH_DATA, verify_ssl_certs=False, max_tokens=512)
        self.database = ProductDatabase()
        self.database.load()
        self.database.save()

    def get_interests(self, context: ClientContext, user_message):
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_interests),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", user_message),
            ("ai", bot_interests),
            ("human", human_interests),
        ])
        chain = prompt | self.llm | StrOutputParser()
        interests = chain.invoke({
            "chat_history": context.messages,
            "interests": context.interests
        })
        return interests

    def search_products(self, context: ClientContext, user_message) -> List[Tuple[Product, str]]:
        query = context.interests
        products = self.database.search_best_offers(query)
        products_with_reasons = [(p, self.get_product_reason(context, user_message, p)) for p in products]
        return products_with_reasons

    def get_product_reason(self, context: ClientContext, user_message, product) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_reason),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", user_message),
            ("ai", bot_reason),
            ("human", human_reason),
        ])
        chain = prompt | self.llm | StrOutputParser()
        reason = chain.invoke({
            "chat_history": context.messages,
            "interests": context.interests,
            "product": product.full_text,
        })
        return reason

    def ask_question(self, context: ClientContext, user_message):
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_ask),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", user_message),
            ("ai", bot_ask),
            ("human", human_ask),
        ])
        chain = prompt | self.llm | StrOutputParser()
        question = chain.invoke({
            "chat_history": context.messages,
            "interests": context.interests
        })

        return question

    def get_options(self, context: ClientContext, user_message, question):
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_options),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", user_message),
            ("ai", bot_options),
            ("human", human_options)
        ])
        chain = prompt | self.llm | StrOutputParser()
        options = chain.invoke({
            "chat_history": context.messages,
            "question": question
        })
        try:
            options = json.loads(options)
        except:
            options = None

        return options

    def chat_single(self, context: ClientContext, user_message: str, typing_cb = None) -> Tuple[ClientContext, str, str, List[str], List[Tuple[Product, str]]]:
        if typing_cb:
            typing_cb()

        interests = self.get_interests(context, user_message)
        context.interests = interests
        if typing_cb:
            typing_cb()

        products = self.search_products(context, user_message)
        if typing_cb:
            typing_cb()

        question = self.ask_question(context, user_message)
        if typing_cb:
            typing_cb()

        options = self.get_options(context, user_message, question)

        context.messages += [
            ("human", user_message),
            ("ai", question),
        ]

        return context, interests, question, options, products

    def chat(self):
        messages = [
            "Привет! Где можно погулять в Москве?",
            "Даже не знаю, я пока не понял, что мне нужно",
            "Гулять по паркам",
            "Спасибо, а в парке горького что есть классного?",
            "А расскажи про арку главного входа"
        ]

        start_message = "Добрый день! Я помогу вам найти интересные места!"
        context = ClientContext()
        context.messages = [("ai", start_message)]
        print("Bot :", start_message)
        # while True:
        #     message = input()
        for message in messages:
            print("User:", message)
            context, output_message, options = self.chat_single(context, message)
            print("Bot :", output_message)
            print(options)


def main():
    bot = Assistant(verbose=True)

    bot.chat()


if __name__ == '__main__':
    main()
