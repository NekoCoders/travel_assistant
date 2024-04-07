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

    $.ajax({
      type: "POST",
      url: "send_message",
      data: formData,
      dataType: "json",
      encode: true,
      headers: {'X-CSRFToken': csrf},
      mode: 'same-origin' // Do not send CSRF token to another domain.
    }).done(function (data) {
          var message_to_append = `
            <div class="message">
                    <div class="photo" style="background-image: url(static/Images/Boris.jpeg);">

                    </div>
                    <p class="text">${data.message}</p>
            </div>`;
          $(".messages-chat").append(message_to_append);
          render_options(data.options);
    });

    $("#write-message").val("");
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

});