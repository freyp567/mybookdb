/*
wiring for bootstrap-table displaying books 

http://bootstrap-table.wenzhixin.net.cn/documentation/
*/

let book_id = 987654321;

function format_book_link(value, row, index) {
  return "<a href='/bookshelf/book/"+row.id+"'>"+value+"</a>";
}

function format_state(value, row, index){
  let status = "";
  if (row.states__haveRead) {
    status += "have read";
  } else {
    if (row.states__readingNow) {
      status += "reading";
    } else {
      if (row.states__toBuy) {
        status += "want read";
      }
      else {
        status += "NOT read";
      }
    }
  }
  
  var status_url = url_status_base.replace(/987654321/, row.id);
  status = '<a data-toggle="modal" data-target="#states-modal" href="' +status_url +'" >' +status +'</a>';
  return status;

}


$('#states-modal').on('show.bs.modal', function (event) {
    var status_url = url_status_base.replace(/987654321/, book_id);
    var modal = $(this);
    $.ajax({
        url: status_url,
        context: document.body
    }).done(function(response) {
        modal.html(response);
    });
})


// workaround for issue with bootstrap-table filter-control and cookie 
const filter_control = Cookies.get('books.bs.table.filterControl');
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
  // path: '/bookshelf/books/v2'
  const cookie_value = [{'field':'title','text':''}];
  JSONCookies.set('books.bs.table.filterControl', cookie_value, { expires: 1 });
}


if ($('#bookslist').length !== 0) {
  console.info("initialize bootstrap table bookslist");
  const $table = $('#bookslist');
  
  $table.bootstrapTable({
    url: '/bookshelf/books/search',
  });

  $table.on('expand-row.bs.table', function(e, index, row, $detail) {
    console.info("expand-row.bs.table index=" +index);
    const res = JSON.stringify(row);
    console.debug("expand row#" +index +": " +res);
      $detail.html(res);
    book_id = row["id"];
    const url = `/bookshelf/book/${book_id}/listdetails`;
    console.debug("details from " +url);
    $.get(url, (res) => {
      $detail.html(res);
    });
  });
  
  
  $table.on("click-row.bs.table", function(e, row, $tr) {
    console.debug("clicked on table row/cell: " + $(e.target).attr('class'), [e, row, $tr]);
    //let row_num = $tr.index() + 1;
    book_id = row["id"];
    // trigger expands row with text detailFormatter..
    if ($tr.next().is('tr.detail-view')) {
      $table.bootstrapTable('collapseRow', $tr.data('index'));
    } else {
      $table.bootstrapTable('expandRow', $tr.data('index'));
    }
  });

} else {
  console.error("bootstrap table bookslist not found");
}


