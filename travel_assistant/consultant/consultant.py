# from langchain.schema import HumanMessage, SystemMessage
import json
from typing import List, Tuple

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models.gigachat import GigaChat
from langchain_core.prompts import ChatPromptTemplate

from travel_assistant.common.custom_types import Product
from travel_assistant.common.gigachat_api import AUTH_DATA
from travel_assistant.database.database import ProductDatabase


class Consultant:
    def __init__(self):
        self.llm = GigaChat(model="GigaChat", credentials=AUTH_DATA, verify_ssl_certs=False)
        self.database = ProductDatabase()
        self.database.load()

    def collect_data(self, history: ChatPromptTemplate):
        key_parameters = {
            "city": {
                "description": "Город, в которм происходит мероприятие, или в котором расположен объект",
                "examples": ["Москва", "Краснодар", "Мурманск"],
            },
            "vacation_kind": {
                "description": "Вид отдыха по типу занятия",
                "examples": ["активный", "экстрим", "пляжный", "прогулка", "семейный"],
            },
            "duration": {
                "description": "Продолжительность отдыха или прогулки, которую планирует клиент, в днях",
                "examples": [],
            },
            "start_date": {
                "description": "Дата начала путешествия",
                "examples": [],
            },
        }

        formatted_schema = "{\n"
        for key, data in key_parameters.items():
            args = '" | "'.join(data["examples"])
            block = f'  //{data["description"]}\n  "{key}": // "{args}" | "" | List[a, b, c, ...] | ...\n\n'
            formatted_schema += block
        formatted_schema += "}"
        # print(formatted_schema)
        # formatted_schema = ""
        # formatted_schema += "city -- Город, в которм происходит мероприятие, или в котором расположен объект\n"
        # formatted_schema += "vacation_kind -- Вид отдыха по типу занятия\n"
        # formatted_schema += "duration -- Продолжительность отдыха или прогулки, которую планирует клиент\n"

        prompt = history + ChatPromptTemplate.from_messages([
            ("ai", "Спасибо за ваш ответ, я должен его учесть, чтобы предложить вам подходящие варианты отдыха."),
            ("human", "Предлагаю тебе собрать всю нужную информацию о том, какой тур мне нужен, из истории нашего диалога и заполнить ее в виде JSON объекта."),
        ])
        # prompt = prompt.partial(schema=formatted_schema)

        # print(prompt.format())

        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({})
        # print(f"My thoughts: --->>>\n{response}")
        # prompt.append(AIMessage(f"{response}"))
        # prompt.append(HumanMessage(f"Спасибо! Теперь выдели из найденной тобой ранее информации значения этих полей: \n{formatted_schema}\nЕсли в прошлом не дано значение какого-то из полей, то пропусти его и не добавляй в JSON."))
        # response = chain.invoke({})
        # print(f"My thoughts: --->>>\n{response}")
        # collected_data = json.loads(response)
        collected_data = response

        prompt2 = ChatPromptTemplate.from_messages([
            ("system", "Опиши примерно путешествие по России или прогулку в какое-то место в городе России, которое будет удовлетворять указанным параметрам"),
            # ("human", "Город: {city}, Тип отдыха: {vacation_kind}, Продолжительность: {duration}"),
            HumanMessage(f"{collected_data}"),
        # ]).partial(**collected_data)
        ])
        chain2 = prompt2 | self.llm | StrOutputParser()
        response = chain2.invoke({})
        # print(f"My thoughts: --->>>\n{response}")
        query = response

        products = self.database.search_best_offers(query)
        print(json.dumps([p.full_text for p in products], indent=2, ensure_ascii=False))
        question, options = self.ask_question(products)

        # print(question)
        # print(options)
        return question, options

    def chat(self):
        start_message = "Добрый день! Я помогу вам подобрать подходящий тур! Что вас интересует?"

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Ты - туристический консультант, который предлагает клиентам идеи для прогулок и маршрутов, где можно посмотреть разные достопримечательности. Очень важно, что ты предлагаешь туры только по России, а также прогулки по городам и жкскурсии по интересным местам."),
            ("ai", start_message),
        ])

        chain = prompt | self.llm | StrOutputParser()

        messages = [
            "я хочу на море",
            "черное море",
            "Сочи и Абхазия",
            "я бы еще хотел проверить, что на курорте сейчас пляжный сезон",
            "кстати я хочу поехать на две недели",
        ]

        # prompt.append(("human", messages[0]))

        print(start_message)
        # message = input()
        # prompt.append(("human", message))
        #
        # response = chain.invoke({})
        # print(response)
        # prompt.append(("ai", response))
        # query = response
        #
        # products = self.database.search_best_offers(query)
        # print(json.dumps([p.full_text for p in products], indent=2, ensure_ascii=False))
        # question, options = self.ask_question(products)
        # print(question)
        # print(options)

        # for message in messages:
        while True:
            message = input()
            prompt.append(("human", message))

            response = chain.invoke({})
            print(response)
            prompt.append(("ai", response))

            question, options = self.collect_data(prompt)
            # prompt.append(("ai", question))
            print(question)
            print(options)

            # prompt.append(("human", options[0]))

            # response = chain.invoke({})
            # print(response)
            # prompt.append(("ai", response))

        print(prompt.format())

    def ask_question(self, product_offers: List[Product]) -> Tuple[str, List[str]]:
        sep = "\n----------------------------------\n"

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Ты - туристический консультант, который предлагает клиентам идеи для прогулок и маршрутов, где можно посмотреть разные достопримечательности."),
            ("ai", "Я подобрал для вас несколько интересных вариантов, куда можно пойти: {sep}{descriptions}{sep}. Все это разные места."),
            ("human", "Спасибо! А расскажи, чем эти варианты отличаются?"),
        ])

        prompt = prompt.partial(descriptions=f"{sep}".join([p.full_text for p in product_offers]), sep=sep)

        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke({})
        # print(response)

        prompt.append(("ai", response))
        prompt.append(("human", "Спроси у меня что-нибудь, чтобы мне было проще выбрать что-то, может быть похожее, что мне нравится... Постарайся не копировать и не использовать названия из описаний"))
        response = chain.invoke({})

        question = response

        prompt.append(("ai", response))
        prompt.append(("human", "Предложи мне варианты ответа. Варианты напиши в виде json списка"))
        response = chain.invoke({})
        options = json.loads(response)

        return question, options


def main():
    bot = Consultant()

    bot.chat()


if __name__ == '__main__':
    main()
