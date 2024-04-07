import dataclasses
import json
from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import render

from travel_assistant.common.custom_types import ClientContext
from travel_assistant.consultant.assistant import Assistant


# Create your views here.
def main_page(request):
    return render(request, 'RussPass.html')


context_by_chat_id: dict[str, ClientContext] = defaultdict(ClientContext)
assistant = Assistant(verbose=True)


def form_send_message(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        message_text = request.POST.get("message_text", "")
        csrf = request.POST.get("csrf", "")

        # Обращение к боту
        old_context = context_by_chat_id[csrf]
        new_context_by_chat_id, bot_message, bot_question, options, products = assistant.chat_single(old_context,
                                                                                                     message_text)
        for p in products:
            p.emb = None
        ready_products = [dataclasses.asdict(p) for p in products]
        response_data = {'message': bot_message + "\n" + bot_question, 'options': options, 'products': ready_products}
    else:
        response_data = {}
    return HttpResponse(json.dumps(response_data), content_type="application/json")
