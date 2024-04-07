render_products = function(products) {
  var products_container = $(".discussions");
  products_container.text("");
  products.forEach(element => {
    var new_element = `
      <div class="discussion">
        <div class="photo" style="background-image: url(https://russpass.ru/mesta-i-sobytiya/_next/image?url=https://cms.russpass.ru/v1/file/${element.product.id}/924&w=750&q=75);"></div>
        <div class="desc-contact">
          <a href="https://russpass.ru/event/{element.product.id}"><p class="name">${element.product.title}</p></a>
          <p class="message">${element.description}</p>
        </div>
        <button class="like">
          <i class=" fa fa-heart" aria-hidden="true"></i>
        </button>
      </div>
    `;
    products_container.append(new_element);
  });


}

render_options = function(option_texts) {
    $(".avtotvet").each(function( index ) {
        if (index < option_texts.length) {
            $( this ).text(option_texts[index]);
        }
    });
}

send_message = function() {
    var messages_container = $(".messages-chat");
    var message_text = $("#write-message").val();
    var csrf = $("input[name=csrfmiddlewaretoken]").val();
    console.log(csrf);
    var formData = {
      message_text: message_text,
      csrf: csrf,
    };

    var message_to_append = `
          <div class="message text-only">
                <div class="response">
                  <p class="text">${message_text}</p>
                </div>
          </div>`;
    $(".messages-chat").append(message_to_append);
    $('.messages-chat').scrollTop($('.messages-chat')[0].scrollHeight);
    $('.text-typing').show();

    $.ajax({
      type: "POST",
      url: "send_message",
      data: formData,
      dataType: "json",
      encode: true,
      headers: {'X-CSRFToken': csrf},
      mode: 'same-origin' // Do not send CSRF token to another domain.
    }).done(function (data) {
          $('.text-typing').hide();
          var message_to_append = `
            <div class="message">
                    <div class="photo" style="background-image: url(static/Images/Boris.jpeg);">

                    </div>
                    <p class="text">${data.message}</p>
            </div>`;
          $(".messages-chat").append(message_to_append);
          render_options(data.options);
          render_products(data.products);
    });

    $("#write-message").val("");
    $('.text-typing').hide();
}

$(document).ready(function (event) {
     $('#write-message').on('keypress', function (e) {
         if(e.which === 13){

            //Disable textbox to prevent multiple submit
            $(this).attr("disabled", "disabled");

            send_message();

            //Enable the textbox again if needed.
            $(this).removeAttr("disabled");
            //event.preventDefault();
         }
   });

  $("#send-message").on( "click", function(event) {
        send_message();
        //event.preventDefault();
  });

    $(".avtotvet").on( "click", function(event) {
        var message_text = $("#write-message").val($(this).text());
        send_message();
        //event.preventDefault();
  });

});