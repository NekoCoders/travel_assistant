# from langchain.schema import HumanMessage, SystemMessage
import json
from typing import List, Tuple

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models.gigachat import GigaChat
from langchain_core.prompts import ChatPromptTemplate

from travel_assistant.common.custom_types import Product
from travel_assistant.common.gigachat_api import AUTH_DATA


def ask_question(product_offers: List[Product]) -> Tuple[str, List[str]]:
    llm = GigaChat(model="GigaChat", credentials=AUTH_DATA, verify_ssl_certs=False)

    sep = "\n----------------------------------\n"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Ты - туристический консультант, который предлагает клиентам идеи для прогулок и маршрутов, где можно посмотреть разные достопримечательности."),
            ("ai", "Я подобрал для вас несколько интересных вариантов, куда можно пойти: {sep}{descriptions}{sep}. Все это разные места."),
            ("human", "Спасибо! А расскажи, чем эти варианты отличаются?"),
        ]
    )

    prompt = prompt.partial(descriptions=f"{sep}".join([p.description for p in product_offers]), sep=sep)

    chain = prompt | llm | StrOutputParser()

    response = chain.invoke({})
    print(response)

    prompt.append(AIMessage(response))
    prompt.append(HumanMessage("Спроси у меня что-нибудь, чтобы мне было проще выбрать что-то похожее, но может быть другое, что мне нравится... Постарайся не копировать и не использовать текст из описаний и прояви фантазию!"))
    response = chain.invoke({})

    question = response

    prompt.append(AIMessage(response))
    prompt.append(HumanMessage("Предложи мне варианты ответа. Варианты напиши в виде json списка"))
    response = chain.invoke({})
    options = json.loads(response)

    return question, options

