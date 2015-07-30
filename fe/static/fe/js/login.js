/**
 * Eventure
 *
 * login.js
 * @author    Eventure Dev Team
 * @copyright Copyright (c) 2015 Eventure (http://www.eventure.com)
 */

$(document).ready(function(){
    $(".tabs .tab, a.tab").click(function(){
        $(".tabs .tab").removeClass("selected");
        if ($(this).html() === 'Login'){
            $(".tabs .tab.login").addClass("selected");
            $("#login").removeClass("hidden-form");
            $("#create-account").addClass("hidden-form");
        } else {
            $(".tabs .tab.create-account").addClass("selected");
            $("#create-account").removeClass("hidden-form");
            $("#login").addClass("hidden-form");
        }
    });// End of click

    $("form#create-account-form").submit(function(e){
        var accountsApiUrl = ACCOUNTS_API_URL;
        var $submitButton = $('#create-account .btn-default');
        var $inputBox = $('#create-account-form input');
        var $formGroup = $("#create-account-form .form-group:nth-child(1),#create-account-form .form-group:nth-child(2)");
        var $helprBlock = $('#create-account-form .form-group.has-error .help-block');
        var postData = $(this).serializeArray();
        $submitButton.attr("disabled", true);
        $.ajax({
            type: "POST",
            url: accountsApiUrl,
            headers: {
                'X-CSRFToken': CSRF_TOKEN
            },
            data: postData,
            dataType: "json",
            crossDomain: true,
            success: function (data) {
                console.log("success", data);
                $formGroup.removeClass("has-error");
                $helprBlock.remove();
                $inputBox.attr("disabled", true);
                $('.tab-wrapper').html('<section id="create-account-email-sent"><div class="row"><div class="text-center"><p>We will be sending you an email with a link <br>to verify that this is you.<p>Click the link in the email to finish creating your account.</p></div></div><div class="row"><div class="text-center"><a href="#" class="col-xs-6 col-centered btn btn-default">Ok, got it.</a></div></div></section>');
            },
            error: function (data) {
                // error handler
                console.log("failed", data);
                $helprBlock.remove();
                $formGroup.addClass("has-error");
                var errorHTML = '';
                $.each(data.responseJSON, function(i,err){
                    errorHTML += '<p class="help-block">' + err + '</p>';
                });
                $submitButton.attr("disabled", false);
                $("#create-account-form .form-group.has-error").append(errorHTML);
            }
        });
        e.preventDefault();
    });// End of Submit
    // $("#create-account-email-sent .btn-default").click(function(){
        
    // });// End of click
});// End of ready