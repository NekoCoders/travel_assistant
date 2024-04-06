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
from travel_assistant.database.database import ProductDatabase


system = '''Ты - туристический консультант, твоя задача - подобрать для клиента места, экскурсии и маршруты, которые бы его заинтересовали.
Ты взаимодействуешь с пользователем не напрямую, а через систему.
Пользователь скорее всего не знает, чего он хочет, и тебе нужно его заинтересовать.
Ты можешь задавать ему вопросы, чтобы выяснить, что ему бы понравилось.
Также если пользователь что-то у тебя спросит, попробуй найти информацию об этом.

Система позволяет тебе использовать следующие инструменты:
{tool_names}

Сначала подумай, какой инструмент ты будешь использовать.
Подумай также, какие данные ты подашь на вход этого инструмента.
Опиши это словами и запиши свои мысли в таком формате:
Thoughts: <твои рассуждения>

Теперь, чтобы система могла запустить выбранный тобой инструмент, сформулируй аргументы в виде JSON объекта.
{{
    "action": "<tool name>",
    "action_input": {{
        "<argument1>": "<value1>",
        "<argument2>": "<value2>",
        ...
    }}
}}

Если ты хочешь дать пользователю ответ, используй специальный инструмент "Final Answer".
Пример, как это сделать:
{{
    "action": "Final Answer",
    "action_input": {{
        "result": "<сообщение пользователю в виде текста>"
    }}
}}

Если ты хочешь задать пользователю вопрос, то используй также команду "Final Answer".
Пример, как это сделать:
{{
    "action": "Final Answer",
    "action_input": {{
        "question": "<вопрос пользователю>",
        "options": [
            <вариант1>,
            <вариант2>,
            ...
        ]
    }}
}}

Вот и вся инструкция! Теперь ознакомься со списком инструментов:
{tools}

Можем начинать!
'''

human = '''Привет! Я система, с которой ты взаимодействуешь. Я умею парсить твой ответ и запускать инструменты по твоей команде.
Пользователь задал нам вопрос: {input}
{agent_scratchpad}

Формат твоего ответа:
Thoughts: <твои рассуждения>
{{
    "action": "<action name>" | "Final Answer",
    "action_input": {{
        "<argument1>": "<value1>",
        "<argument2>": "<value2>",
        ...
    }}
}}

Опиши свои дальнейшие действия и сформируй JSON объект для запуска инструмента.
Если ты хочешь передать сообщение пользователю, используй специальный инструмент "Final Answer".
Если ты хочешь задать пользователю вопрос, то используй также команду "Final Answer".
Свой ответ дай в виде JSON'''


def convert_intermediate_steps(intermediate_steps):
    log = ""
    if len(intermediate_steps) > 0:
        log += "Я произвел анализ интересных мест в базе RUSSPASS и получил такие результаты:\n"
    for action, observation in intermediate_steps:
        log += f"{observation}"
    # print(log)
    return log


def parse_json_in_text(
    json_string: str, *, parser: Callable[[str], Any] = parse_partial_json
) -> dict:
    # Try to find JSON string within triple backticks
    # match = re.search(r"```(json)?(.*)", json_string, re.DOTALL)
    match = re.search(r"{(.*)}", json_string, re.DOTALL)

    # If no match found, assume the entire string is a JSON string
    if match is None:
        json_str = json_string
    else:
        # If match found, use the content within the backticks
        json_str = match.group(0)

    # Strip whitespace and newlines from the start and end
    json_str = json_str.strip().strip("`")

    # handle newlines and other special characters inside the returned value
    json_str = _custom_parser(json_str)

    # Parse the JSON string into a Python dictionary
    parsed = parser(json_str)

    return parsed

class CustomJSONAgentOutputParser(AgentOutputParser):
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            response = parse_json_in_text(text)
            if isinstance(response, list):
                # gpt turbo frequently ignores the directive to emit a single action
                # logger.warning("Got multiple action responses: %s", response)
                response = response[0]
            if response["action"] == "Final Answer":
                return AgentFinish({"output": response["action_input"]}, text)
            else:
                return AgentAction(
                    response["action"], response.get("action_input", {}), text
                )
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e

    @property
    def _type(self) -> str:
        return "json-agent"

def create_agent(prompt, llm, tools, tools_renderer: ToolsRenderer = render_text_description_and_args):
    missing_vars = {"tools", "tool_names", "agent_scratchpad"}.difference(
        prompt.input_variables
    )
    if missing_vars:
        raise ValueError(f"Prompt missing required variables: {missing_vars}")

    prompt = prompt.partial(
        tools=tools_renderer(list(tools)),
        tool_names=", ".join([t.name for t in tools]),
    )
    llm_with_stop = llm.bind(stop=["Observation"])

    agent = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: convert_intermediate_steps(x["intermediate_steps"]),
        )
        | prompt
        | llm_with_stop
        | CustomJSONAgentOutputParser()
    )

    return agent


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

        @tool
        def make_questions(interests: str | List[str]) -> str:
            """
            Данный инструмент позволяет сформировать наводящие вопросы для пользователя, которые помогут лучше понять, что его бы заинтересовало и сузить круг поиска.

            :param interests: Интересы пользователя, которые были выяснены в ходе диалога
            :return: Вопросы, которые можно задать пользователю
            """
            questions = [
                {
                    "question": "Что вы больше любите: гулять по паркам или заниматься спортом?",
                    "options": [
                        "Гулять по паркам",
                        "Заниматься спортом",
                    ]
                }
            ]

            output_info = f"\nВопросы, которые можно задать по теме '{interests}':\n"
            output_info += "\n".join([f" - {quest['question']}: {quest['options']}" for quest in questions])
            output_info += "\n"

            return output_info

        tool_list = [search_places, make_questions]

        agent = create_agent(prompt, llm, tool_list)

        agent_executor = AgentExecutor(agent=agent, tools=tool_list, verbose=True)

        agent_output = agent_executor.invoke(
            {
                "input": user_message,
                "chat_history": context,
            }
        )
        response_dict = agent_output["output"]
        if "question" in response_dict:
            response = f"{response_dict['question']}"
            if "options" in response_dict:
                response += f": {response_dict['options']}"
        else:
            response = response_dict["result"]

        context += [
            ("human", user_message),
            ("ai", response)
        ]

        return response, context

    def chat(self):
        messages = [
            "Привет! Где можно погулять в Москве?",
            "Даже не знаю, я пока не понял, что мне нужно",
            "Гулять по паркам",
            "Спасибо, а в парке горького что есть классного?"
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


def main():
    bot = Assistant()

    bot.chat()


if __name__ == '__main__':
    main()
