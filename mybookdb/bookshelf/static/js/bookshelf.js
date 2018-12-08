
function show_table_loaderror(msg_id_sel, details) {
    $alert = $(msg_id_sel);
    // let pos = details.indexOf('Django Version');
    let pos = details.indexOf('Request Method');
    if (pos > 0) {
        // strip diagnostic info not relevant for user
        details = details.substring(0, pos);
        details = details.replace(/(?:\r\n|\r|\n)/g, '<br>');
    }    
    $alert.html('<span>Fehler beim Laden der Tabelle</span>'+
        '<button type="button" class="close" data-dismiss="alert" aria-label="Close">'+
        '  <span aria-hidden="true">&times;</span>'+
        '</button>'+
        '<span>'+details+'</span>'
        );
    $alert.alert();
    $alert.slideDown();  // .fadeIn();
}

