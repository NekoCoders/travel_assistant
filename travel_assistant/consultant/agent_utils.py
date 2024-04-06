import re
from typing import Union, Callable, Any

from langchain.agents import AgentOutputParser
from langchain.tools.render import ToolsRenderer, render_text_description_and_args
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers.json import _custom_parser, parse_partial_json
from langchain_core.runnables import RunnablePassthrough


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
        parsed = {"action": "Final Answer", "action_input": {"answer": json_str}}
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
            if response["action"] == "answer":
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