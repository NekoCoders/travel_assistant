from django.shortcuts import render


# Create your views here.
def main_page(request):
    return render(request, 'RussPass.html')


def form_send_message(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = FeedbackForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            message = (f"Заявка на сайте от {form.cleaned_data['name']} {form.cleaned_data['surname']}, "
                       f"свяжитесь по телефону {form.cleaned_data['tel']}")
            send_feedback_notification(message=message)
            # тут отобразить начальную страницу с доп параметром - покажи всплывающее окно!
            return HttpResponseRedirect("/")
    else:
        return HttpResponseRedirect("/")

    return render(request, "name.html")
