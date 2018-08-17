/*
wiring for bootstrap-table displaying books 

http://bootstrap-table.wenzhixin.net.cn/documentation/
*/

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
  console.error("initialize bootstrap table bookslist");
  
  $('#bookslist').bootstrapTable({
    url: '/bookshelf/books/search',
  });
  
} else {
  console.error("bootstrap table bookslist not found");
}

/*
    queryParams: function(params) {
      params['title'] = $('#col-title').text();
      params['created'] = $('#col-created').text();
      params['updated'] = $('#col-updated').text();
      return params;
    },
    # queryParamsType: 'limit' # data-query-params-type

*/
