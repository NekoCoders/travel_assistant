from __future__ import annotations

import json
from typing import List, Tuple

from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models.gigachat import GigaChat
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, tool

from travel_assistant.common.gigachat_api import AUTH_DATA
from travel_assistant.consultant.agent_utils import create_agent
from travel_assistant.consultant.assistant_prompts import system, human, system_ask, human_ask
from travel_assistant.database.database import ProductDatabase


class Assistant:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.llm = GigaChat(model="GigaChat", credentials=AUTH_DATA, verify_ssl_certs=False)
        self.database = ProductDatabase()
        self.database.load()
        self.database.save()

        self.tools = []
        self.register_search_places_tool()

        self.create_agent()

    def register_search_places_tool(self):
      @tool
      def search_places(query: str) -> str:
        """
        Данный инструмент позволяет найти в базе RUSSPASS места для прогулки или путешествия по их описанию.
        Используй этот инструмент всегда, когда готов порекомендовать пользователю места.

        :param query: Описание места, которое вы бы хотели посетить
        :return: Предложения, которые есть в базе
        """
        products = self.database.search_best_offers(query)
        output_info = f"\nПредложения, которые я нашел в базе RUSSPASS по запросу '{query}':\n"
        output_info += "\n".join([f" - {p.title}: {p.description}" for p in products])
        output_info += "\n"

        return output_info
      self.tools.append(search_places)

    def create_agent(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", human),
        ])

        agent = create_agent(prompt, self.llm, self.tools)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=self.verbose)

    def chat_single(self, context: List[Tuple[str, str]], user_message: str) -> Tuple[List[Tuple[str, str]], str, List[str]]:
        agent_output = self.agent_executor.invoke(
            {
                "input": user_message,
                "chat_history": context,
            }
        )
        bot_response = agent_output["output"]
        if isinstance(bot_response, dict):
            bot_response = bot_response.values().__iter__().__next__()

        question, options = self.ask_questions(context, bot_response)

        full_response = f"{bot_response}\n{question}"

        context += [
            ("human", user_message),
            ("ai", full_response)
        ]

        return context, full_response, options

    def chat(self):
        messages = [
            "Привет! Где можно погулять в Москве?",
            "Даже не знаю, я пока не понял, что мне нужно",
            "Гулять по паркам",
            "Спасибо, а в парке горького что есть классного?",
            "А расскажи про арку главного входа"
        ]

        start_message = "Добрый день! Я помогу вам найти интересные места!"
        context = [("ai", start_message)]
        print("Bot :", start_message)
        # while True:
        #     message = input()
        for message in messages:
            print("User:", message)
            context, output_message, options = self.chat_single(context, message)
            print("Bot :", output_message)
            print(options)

    def ask_questions(self, context, bot_response):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_ask),
                MessagesPlaceholder("chat_history", optional=True),
                ("ai", bot_response),
                ("human", human_ask),
            ]
        )

        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke({"chat_history": context})
        response = json.loads(response)
        question = response["question"]
        options = response["options"]

        return question, options


def main():
    bot = Assistant(verbose=True)

    bot.chat()


if __name__ == '__main__':
    main()
