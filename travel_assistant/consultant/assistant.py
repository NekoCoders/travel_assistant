# from langchain.schema import HumanMessage, SystemMessage
from __future__ import annotations

import json
import re
from typing import List, Tuple, Union, Callable, Any

from langchain.agents.format_scratchpad import format_log_to_str
from langchain.agents.output_parsers import XMLAgentOutputParser, JSONAgentOutputParser
from langchain.tools.render import ToolsRenderer, render_text_description_and_args
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models.gigachat import GigaChat
from langchain_core.output_parsers.json import parse_partial_json, _custom_parser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain import hub
from langchain.agents import AgentExecutor, tool, create_structured_chat_agent, AgentOutputParser
from langchain_core.runnables import RunnablePassthrough

from travel_assistant.common.custom_types import Product
from travel_assistant.common.gigachat_api import AUTH_DATA
from travel_assistant.consultant.agent_utils import create_agent
from travel_assistant.consultant.assistant_prompts import system, human, system_ask, human_ask
from travel_assistant.database.database import ProductDatabase


class Assistant:
    def __init__(self):
        self.llm = GigaChat(model="GigaChat", credentials=AUTH_DATA, verify_ssl_certs=False)
        self.database = ProductDatabase()
        self.database.load()
        self.database.save()

    def chat_single(self, context: List[Tuple[str, str]], user_message: str):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", human),
            ]
        )

        llm = self.llm.bind(function_call="none")

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

        tool_list = [search_places]

        agent = create_agent(prompt, llm, tool_list)

        agent_executor = AgentExecutor(agent=agent, tools=tool_list, verbose=True)

        agent_output = agent_executor.invoke(
            {
                "input": user_message,
                "chat_history": context,
            }
        )
        bot_response = agent_output["output"]["text"]

        question, options = self.ask_questions(context, bot_response)

        full_response = f"{bot_response}\n{question}"
        print(options)

        context += [
            ("human", user_message),
            ("ai", full_response)
        ]

        return full_response, context

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
            output_message, context = self.chat_single(context, message)
            print("Bot :", output_message)

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
    bot = Assistant()

    bot.chat()


if __name__ == '__main__':
    main()
