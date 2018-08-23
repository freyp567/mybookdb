/*
wiring for bootstrap-table displaying authors 

http://bootstrap-table.wenzhixin.net.cn/documentation/

detailFormatter adapted from 
https://jsfiddle.net/dabros/6ony6cs2/1/

*/

// workaround for issue with bootstrap-table filter-control and cookie 
const filter_control = Cookies.get('authors.bs.table.filterControl');
if (!filter_control) {
  JSONCookies = Cookies.withConverter({
      read: function(value, name) {
          //return cookie.replace(rdecode, decodeURIComponent);
          return value;
      },
      write: function (value, name) {
          return value;
      }
  });
  // path: '/bookshelf/authors/v2'
  const cookie_value = [{'field':'title','text':''}];
  JSONCookies.set('authors.bs.table.filterControl', cookie_value, { expires: 1 });
}


// show bootstrap4 titles
$(function () {
  $('[data-toggle="tooltip"]').tooltip();
});


if ($('#authorslist').length !== 0) {
  console.info("initialize bootstrap table authorslist");
  const $table = $('#authorslist');
  
  $table.bootstrapTable({
    url: '/bookshelf/authors/search',
  });
  

  $table.on('expand-row.bs.table', function(e, index, row, $detail) {
    //var res = $("#desc" + index).html();
    const res = JSON.stringify(row);
    console.debug("expand row#" +index +": " +res);
      $detail.html(res);
    const author_id = row["id"];
    const url = `/bookshelf/author/${author_id}/listdetails`;
    console.debug("details from " +url);
    $.get(url, (res) => {
      $detail.html(res);
      $('.book_tooltip').tooltip({
        container: 'body'
      });
    });
  });
  
  $table.on("click-row.bs.table", function(e, row, $tr) {
  
    // prints Clicked on: table table-hover, no matter if you click on row or detail-icon
    console.debug("clicked on table row/cell: " + $(e.target).attr('class'), [e, row, $tr]);
  
    // trigger expands row with text detailFormatter..
    //$tr.find(">td>.detail-icon").trigger("click");
    // $tr.find(">td>.detail-icon").triggerHandler("click");
    if ($tr.next().is('tr.detail-view')) {
      $table.bootstrapTable('collapseRow', $tr.data('index'));
    } else {
      $table.bootstrapTable('expandRow', $tr.data('index'));
    }
  });


  
} else {
  console.error("bootstrap table authorslist not found");
}
