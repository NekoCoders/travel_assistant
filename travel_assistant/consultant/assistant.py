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

@tool
def search(query: str) -> str:
    """Поиск информации о температуре в различных местах"""
    return "32 degrees"

tool_list = [search]


# system = '''Постарайся ответить на вопрос человека. You have access to the following tools:
#
# {tools}
#
# Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).
#
# Valid "action" values: "Final Answer" or {tool_names}
#
# Provide only ONE action per $JSON_BLOB, as shown:
#
# ```
# {{
#   "action": $TOOL_NAME,
#   "action_input": $INPUT
# }}
# ```
#
# Follow this format:
#
# Question: input question to answer
# Thought: consider previous and subsequent steps
# Action:
# ```
# $JSON_BLOB
# ```
# Observation: action result
# ... (repeat Thought/Action/Observation N times)
# Thought: I know what to respond
# Action:
# ```
# {{
#   "action": "Final Answer",
#   "action_input": "Final response to human"
# }}
#
# Начинаем
# '''
#
# '''
# Begin! Reminder to ALWAYS respond with a valid json blob of a single action.
# Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation.
# '''
#
# human = '''Question:{input}
# {agent_scratchpad}'''

system = '''
Ты - виртуальный ассистент, который может отвечать на вопрос пользователя.
Пользователь задает тебе вопрос, а ты должен спланировать свои действия, чтобы дать ответ.
Чтобы ответить на вопрос человека, используй вспомогательные инструменты:

{tool_names}

Сначала подумай, какой инструмент ты будешь использовать.
Напиши свои мысли в таком формате:
Thoughts: <твои рассуждения>

Затем прими решение, какой инструмент ты будешь запускать, и напиши свое решение в таком формате:
Action: <инструмент, который будем запускать>

Затем сформируй входные данные для инструмента, который ты выбрал.
Напиши входные данные в формате:
Input: <входные данные>

Сохрани и проанализируй свои мысли.
Теперь, чтобы система могла запустить выбранный тобой инструмент, сформулируй аргументы в виде JSON объекта.
$JSON_BLOB:
```json
{{
    "action": "<action name>",
    "action_input": {{
        ...
    }}
}}
```

Вот и вся инструкция! Теперь ознакомься со списком инструментов.


Список инструментов:
{tools}




Напоминаю формат твоего ответа. Всегда соблюдай его:

assistant:
########################################
Thoughts: <твои рассуждения>
Action: <инструмент, который будем запускать>
Input: <входные данные>
$JSON_BLOB:
```json
{{
    "action": "<action name>",
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
    # llm_with_stop = llm.bind(stop=["Observation: "])
    llm_with_stop = llm

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
        # self.database = ProductDatabase()
        # self.database.load()
        # self.database.save()

    def chat(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                MessagesPlaceholder("chat_history", optional=True),
                ("ai", bot),
                ("human", human),
            ]
        )

        tools = [search]

        llm = self.llm.bind(function_call="none")

        agent = create_agent(prompt, llm, tools)

        agent_executor = AgentExecutor(agent=agent, tools=tool_list, verbose=True)

        result = agent_executor.invoke({"input": "Привет! Какая температура в Москве?"})

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
