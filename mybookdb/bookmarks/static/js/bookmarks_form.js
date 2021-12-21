
function update_bookmarks_form(response) {
    console.debug('response=', response);
    if (response.site_created) {
      // add response.site to id_link_site droplist
      var newOption = new Option(response.site, response.site_id, false, false);
      $('#id_link_site').append(newOption).trigger('change');
      console.debug("added new site=" +response.site);
    }
    $('#id_link_site').val(response.site_id).trigger('change');
    console.debug("picked site=" +response.site);
    $('#id_link_name').val(response.name);
}


$('#id_link_uri').on('change',
    function(e) {
      let value = $('#id_link_uri').val();
      let url = bookmarks_url_parseuri +'?uri=' +encodeURIComponent(value);
      console.debug('link_url changed: ' +url);
      $.ajax({
        url: url
      }).done(function(response) {
        update_bookmarks_form(response);
      }).fail(function( jqXHR, textStatus, errorThrown ) {
        console.error("parse_uri failed", textStatus);
        // TODO error feedback
      });
    });
