 
        
    $('a.internal').each( function ()
    {            
        $(this).click(function()
            {   
            $("#spinner").height($(this).parent().height());
            $("#spinner").width($(this).parent().width());
            $("#spinner").css("top", $(this).parent().offset().top).css("left", $(this).parent().offset().left).show()
            head.js($(this).attr('link-destination') + "?js=yes&timestamp=" + Math.round(new Date().getTime())  );            
            return false;
            });
        $(this).attr("link-destination",this.href);
    });
    $('#spinner').hide();

    $(".usernote").submit(function(event) {
        /* stop form from submitting normally */
        noteref = $(this);
        event.preventDefault(); 
        
        /* get some values from elements on the page: */
        var $form = $( this ),
            rating = $form.find( 'input[name="rating"]' ).val(),
            url = $form.attr( 'action' );

        /* Send the data using post and put the results in a div */
        $.post( url, { 'pubkey': $form.find( 'input[name="pubkey"]' ).val(),
                       '_xsrf' : $form.find( 'input[name="_xsrf"]' ).val(), 
                       'note' : $form.find( 'input[name="note"]' ).val() },
          function( data ) {
              noteref.empty().append( data );
          }
        );
    });        

     $(".vote").submit(function(event) {
        voteref = $(this);
        /* stop form from submitting normally */
        event.preventDefault(); 
        
        /* get some values from elements on the page: */
        var $form = $( this ),
            rating = $form.find( 'input[name="rating"]' ).val(),
            url = $form.attr( 'action' );

        /* Send the data using post and put the results in a div */
        $.post( url, { 'rating': $form.find( 'input[name="rating"]' ).val(),
                       '_xsrf' : $form.find( 'input[name="_xsrf"]' ).val(), 
                       'hash' : $form.find( 'input[name="hash"]' ).val() },
          function( data ) {
              voteref.parent().empty().append( data );
          }
        );
    });                
                
    $(".followtopic").submit(function(event) {
        ref = $(this);
        /* stop form from submitting normally */
        event.preventDefault(); 

        /* get some values from elements on the page: */
        var $form = $( this ),
            url = $form.attr( 'action' );

        /* Send the data using post and put the results in a div */
        $.post( url, {'_xsrf' : $form.find( 'input[name="_xsrf"]' ).val(),'topic' : $form.find( 'input[name="topic"]' ).val() },
          function( data ) {
              ref.empty().append("Done.");
              head.js('/?js=yes&singlediv=left' + "&timestamp=" + Math.round(new Date().getTime())  );            
          }
        );

    });


    $(".followuser").submit(function(event) {
        ref = $(this);
        /* stop form from submitting normally */
        event.preventDefault(); 

        /* get some values from elements on the page: */
        var $form = $( this ),
            url = $form.attr( 'action' );

        /* Send the data using post and put the results in a div */
        $.post( url, {'_xsrf' : $form.find( 'input[name="_xsrf"]' ).val(),'pubkey' : $form.find( 'input[name="pubkey"]' ).val() },
          function( data ) {
              ref.empty().append("Done.");
              head.js('/?js=yes&singlediv=left' + "&timestamp=" + Math.round(new Date().getTime())  );            
          }
        );

    });


    $(".reply").click(function(event) {
        event.preventDefault();
        var $msg = $(this).attr('message');
        var $href = $(this).attr('href');
        $.get($href + "?getonly=true",function(data) {
          $('#reply_'+$msg).empty().append("<br>" + data);
        });   
        
    });  

    $('a.details').each( function ()
    {            
        $(this).click(function()
            {   
            userdiv = "details_" + $(this).attr('user');
            if ($("#" + userdiv).is(":visible"))
            {
                $("#" + userdiv).hide()
            }
            else
            {
                $("#" + userdiv).show()
            }
            return false;
            });
    });