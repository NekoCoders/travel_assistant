$(document).ready(function () {
  $("#send-message").on( "click", function() {
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
    });

    $("#write-message").val("");

  });

  $("form").submit(function (event) {
    var formData = {
      name: $("#name").val(),
      email: $("#email").val(),
      superheroAlias: $("#superheroAlias").val(),
    };

    $.ajax({
      type: "POST",
      url: "process.php",
      data: formData,
      dataType: "json",
      encode: true,
    }).done(function (data) {
      console.log(data);
    });

    event.preventDefault();
  });
});