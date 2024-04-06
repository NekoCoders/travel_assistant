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
    human_options, bot_ask, bot_options, system_interests, bot_interests, human_interests
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

    def search_products(self, interests):
        query = interests
        products = self.database.search_best_offers(query)
        return products

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
        options = json.loads(options)

        return options

    def chat_single(self, context: ClientContext, user_message: str) -> Tuple[ClientContext, str, str, List[str], List[Product]]:
        interests = self.get_interests(context, user_message)
        context.interests = interests

        products = self.search_products(interests)
        question = self.ask_question(context, user_message)
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
