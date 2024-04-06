from __future__ import annotations

import json
from typing import List, Tuple, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models.gigachat import GigaChat
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, tool

from travel_assistant.common.custom_types import Product
from travel_assistant.common.gigachat_api import AUTH_DATA
from travel_assistant.consultant.agent_utils import create_agent
from travel_assistant.consultant.assistant_prompts import system, human, system_ask, human_ask, system_options, \
    human_options
from travel_assistant.database.database import ProductDatabase


class Assistant:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.llm = GigaChat(model="GigaChat", credentials=AUTH_DATA, verify_ssl_certs=False, max_tokens=256)
        self.database = ProductDatabase()
        self.database.load()
        self.database.save()

    def build_tools(self, tool_context: dict):
      @tool
      def search_places(query: str) -> str:
        """
        Данный инструмент позволяет найти в базе RUSSPASS места для прогулки или путешествия по их описанию.

        :param query: Описание места, которое вы бы хотели посетить
        :return: Предложения, которые есть в базе
        """
        products = self.database.search_best_offers(query)
        output_info = f"\nПредложения, которые я нашел в базе RUSSPASS по запросу '{query}':\n"
        output_info += "\n".join([f" - {p.title}. {p.regions}: {p.description}" for p in products])
        output_info += "\n"
        tool_context["products"] = products

        return output_info
      tools = [search_places]
      return tools

    def create_agent(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", human),
        ])

        tool_context = {}
        tools = self.build_tools(tool_context)

        agent = create_agent(prompt, self.llm, tools)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=self.verbose)
        return agent_executor, tool_context

    def chat_single(self, context: List[Tuple[str, str]], user_message: str) -> Tuple[List[Tuple[str, str]], str, str, List[str], Optional[List[Product]]]:
        agent_executor, tool_context = self.create_agent()

        agent_output = agent_executor.invoke(
            {
                "input": user_message,
                "chat_history": context,
            }
        )
        bot_response = agent_output["output"]
        if isinstance(bot_response, dict):
            bot_response = bot_response.values().__iter__().__next__()
        found_products = tool_context["products"] if "products" in tool_context else None

        question, options = self.ask_questions(context, bot_response)

        store_response = f"{bot_response}\nAssistant Question:\n{question}\n"

        context += [
            ("human", user_message),
            ("ai", store_response),
        ]

        return context, bot_response, question, options, found_products

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
        prompt_question = ChatPromptTemplate.from_messages(
            [
                ("system", system_ask),
                MessagesPlaceholder("chat_history", optional=True),
                ("ai", bot_response),
                ("human", human_ask),
            ]
        )
        chain_question = prompt_question | self.llm | StrOutputParser()
        question = chain_question.invoke({"chat_history": context})

        prompt_options = ChatPromptTemplate.from_messages(
            [
                ("system", system_options),
                MessagesPlaceholder("chat_history", optional=True),
                ("ai", f"{bot_response}\n\n{question}"),
                ("human", human_options)
            ]
        )
        chain_options = prompt_options | self.llm | StrOutputParser()
        options = chain_options.invoke({"chat_history": context})
        options = json.loads(options)

        return question, options


def main():
    bot = Assistant(verbose=True)

    bot.chat()


if __name__ == '__main__':
    main()
