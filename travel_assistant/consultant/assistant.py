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


system = '''
Ты - виртуальный ассистент, который может отвечать на вопрос пользователя.
Пользователь задает тебе вопрос, а ты должен спланировать свои действия, чтобы дать ответ.
Чтобы ответить на вопрос человека, используй вспомогательные инструменты:

{tool_names}

Не спеши сразу давать окончательный ответ, сначала постарайся использовать инструменты, которые тебе доступны, чтобы получить актуальную информацию.
Не выдумывай какие-то неизвестные тебе данные сам, вместо этого старайся использовать инструменты, потому что они дают актуальную и более точную информацию.
Сначала подумай, какой инструмент ты будешь использовать.
Подумай также, какие данные ты подашь на вход этого инструмента.
Опиши это словами и запиши свои мысли в таком формате:
Thoughts: <твои рассуждения>

Теперь, чтобы система могла запустить выбранный тобой инструмент, сформулируй аргументы в виде JSON объекта.
```json
{{
    "action": "<tool name>",
    "action_input": {{
        ...
    }}
}}
```

Также в истории диалога сохраняются записи о твоих предыдущих действиях и полученных результатах.
Если в истории достаточно информации, чтобы дать окончательный ответ, то подготовь его.
Если ты хочешь дать окончательный ответ, используй специальный инструмент "Final Answer". 
Пример, как дать окончательный ответ:
```json
{{
    "action": "Final Answer",
    "action_input": "<answer as a string>"
}}
```

Вот и вся инструкция! Теперь ознакомься со списком инструментов.

Список инструментов:
{tools}

Напоминаю формат твоего ответа. Всегда соблюдай только этот формат:
########################################
Thoughts: <твои рассуждения>
```json
{{
    "action": "<action name> | Final Answer",
    "action_input": {{
        ...
    }}
}}
```
########################################

Можем начинать!
'''

human = '''
Question: {input}
'''

bot = '''
Мои предыдущие действия:
{agent_scratchpad}
'''


def convert_intermediate_steps(intermediate_steps):
    log = json.dumps([
        {
            "action": action.tool,
            "action_input": action.tool_input,
            "result": observation
        }
        for action, observation in intermediate_steps
    ], indent=2, ensure_ascii=False)
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

    def chat(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", human),
                ("ai", bot),
            ]
        )

        llm = self.llm.bind(function_call="none")

        @tool
        def search_places(query: str) -> str:
            """
            Данный инструмент позволяет найти в базе RUSSPASS место для прогулки или путешествия по его описанию.

            :param query: Описание места, которое вы бы хотели посетить
            :return: Предложения, которые есть в базе
            """
            products = self.database.search_best_offers(query)
            output_info = "\n\n".join([f"{p.title}: {p.description}" for p in products])

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

    


def main():
    bot = Assistant()

    bot.chat()


if __name__ == '__main__':
    main()
