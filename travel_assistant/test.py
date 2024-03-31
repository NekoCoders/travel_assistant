import json

from travel_assistant.consultant.consultant import Consultant
from travel_assistant.database.database import ProductDatabase


def main():
    # database = ProductDatabase()
    # database.load()
    # database.save()
    #
    # consultant = Consultant()
    #
    # query = "Кладбище кораблей"
    #
    # print(query)
    #
    # results = database.search_best_offers(query, 4)
    # print(json.dumps([p.full_text for p in results], ensure_ascii=False, indent=2))
    #
    # question, options = consultant.ask_question(results)
    #
    # print(question)
    # print(options)
    consultant = Consultant()
    consultant.chat()


if __name__ == '__main__':
    main()