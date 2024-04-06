# from langchain.schema import HumanMessage, SystemMessage
import json
from typing import List, Tuple

from langchain.agents.format_scratchpad import format_log_to_str
from langchain.agents.output_parsers import XMLAgentOutputParser, JSONAgentOutputParser
from langchain.tools.render import ToolsRenderer, render_text_description_and_args
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models.gigachat import GigaChat
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain import hub
from langchain.agents import AgentExecutor, tool, create_structured_chat_agent
from langchain_core.runnables import RunnablePassthrough

from travel_assistant.common.custom_types import Product
from travel_assistant.common.gigachat_api import AUTH_DATA
from travel_assistant.database.database import ProductDatabase


system = '''Ты - туристический консультант, твоя задача - подобрать для клиента места, экскурсии и маршруты, которые бы его заинтересовали.
Ты взаимодействуешь с пользователем не напрямую, а через систему, которая выделяет из твоего ответа специальный Markdown блок с JSON объектом. Ты должен всегда включать в свой ответ такой блок.
Пользователь может задавать тебе вопросы, а ты должен спланировать свои действия, чтобы дать ответ с помощью системы.
Также ты должен пытаться задавать наводящие вопросы, чтобы понять, чего клиент хочет.

Система позволяет тебе использовать следующие инструменты:
{tool_names}

Сначала подумай, какой инструмент ты будешь использовать.
Подумай также, какие данные ты подашь на вход этого инструмента.
Опиши это словами и запиши свои мысли в таком формате:
Thoughts: <твои рассуждения>

Теперь, чтобы система могла запустить выбранный тобой инструмент, сформулируй аргументы в виде JSON объекта.
```json
{{
    "action": "<tool name>",
    "action_input": {{
        "<argument1>": "<value1>",
        "<argument2>": "<value2>",
        ...
    }}
}}
```

Если ты хочешь передать пользователю сообщение или что-то у него спросить, используй специальный инструмент "Final Answer".
Пример, как это сделать:
```json
{{
    "action": "Final Answer",
    "action_input": {{
        "result": "<сообщение пользователю в виде текста>"
    }}
}}
```

Вот и вся инструкция! Теперь ознакомься со списком инструментов.

Список инструментов:
{tools}

Можем начинать!
'''

human = '''Привет! Я система, с которой ты взаимодействуешь. Я умею парсить твой ответ и запускать инструменты по твоей команде.
Пользователь задал нам вопрос: {input}
{agent_scratchpad}
Помни, что ты общаешься не с пользователем, а с системой, которая принимает только Markdown блок с JSON объектом.
Если ты хочешь передать сообщение пользователю, используй специальный инструмент "Final Answer".
Формат твоего ответа:
Thoughts: <твои рассуждения>
```json
{{
    "action": "<action name>" | "Final Answer",
    "action_input": {{
        "<argument1>": "<value1>",
        "<argument2>": "<value2>",
        ...
    }}
}}
```

Опиши свои дальнейшие действия и сформируй Markdown блок с JSON объектом для запуска инструмента.
'''


def convert_intermediate_steps(intermediate_steps):
    log = ""
    if len(intermediate_steps) > 0:
        log += "Я произвел анализ интересных мест в базе RUSSPASS и получил такие результаты:\n"
    for action, observation in intermediate_steps:
        log += f"{observation}"
    return log


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
        | JSONAgentOutputParser()
    )

    return agent


class Assistant:
    def __init__(self):
        self.llm = GigaChat(model="GigaChat", credentials=AUTH_DATA, verify_ssl_certs=False)
        self.database = ProductDatabase()
        self.database.load()
        self.database.save()

    def chat_single(self):
        start_message = "Добрый день! Буду рад подобрать для вас интересные места!"

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("ai", start_message),
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

        result = agent_executor.invoke({"input": "Привет! Где можно погулять в Москве?"})

        # # Using with chat history
        # from langchain_core.messages import AIMessage, HumanMessage
        # result = agent_executor.invoke(
        #     {
        #         "input": "what's my name?",
        #         "chat_history": [
        #             HumanMessage(content="hi! my name is bob"),
        #             AIMessage(content="Hello Bob! How can I assist you today?"),
        #         ],
        #     }
        # )

        print(result)

    # def chat(self):
    #     context = []
    #     print("Добрый день! Я помогу вам подобрать подходящий тур! Что вас интересует?")
    #     while True:
    #         message = input()
    #         output_message, context = self.chat_single(context, message)
    #         print(output_message)

    


def main():
    bot = Assistant()

    bot.chat_single()


if __name__ == '__main__':
    main()
