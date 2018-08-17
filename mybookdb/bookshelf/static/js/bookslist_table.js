/*
wiring for bootstrap-table displaying books 

http://bootstrap-table.wenzhixin.net.cn/documentation/
*/

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
