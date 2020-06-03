/*
handlers for lookup_onleihe.html
*/

function DetailTableRowStyle(row, index) {
    return {
        classes: 'small table-condensed',
        //css: {"font-size": "12px", }
        // "height": "10px"
    }
}

function CustomFormatter(value, row, index) {
    if (row.field_name == "book_url") {
      book_url = value[0];
      img_url = value[1];
      var link_content = "";
      if (img_url) {
        link_content = '<img src = "' + img_url + '" alt = "book details" border = "0"/>';
      }
      else {
        link_content = value[0];
      }
      return "<a href='"+ book_url +"'>" + link_content + "</a>";
    }
    if (row.field_name == "title") {
      return '<span class="book-title-table">' + value +'</span>';
    }
    if (row.field_name == "choice") {
        if (onleiheId == value) {
            return '<input type="radio" id="choice" name="choice" checked value="' +value +'">';
        } else {
            return '<input type="radio" id="choice" name="choice" value="' +value +'">';
        }
    }
    //console.info("customFormatter field_name=" +row.field_name +" index=" +index +" value=" +value);
    // 'book_description' -- prettyprint
    return value;
}

/*
$('#book-detail-table').bootstrapTable({
    data: table_data
});
*/

//  <th data-field="snum" data-formatter="LinkFormatter">Computer</th>
$('#book-detail-table').on('onLoadSuccess.bs.table', function (e, arg1, arg2) {
    console.info("book-detail-table: onLoadSuccess");
});

$('#book-detail-table').on('onLoadError.bs.table', function (e, arg1, arg2) {
    console.error("book-detail-table: onLoadError");
});

$('#book-detail-table').on('onPostBody.bs.table', function (e, arg1, arg2) {
    console.info("book-detail-table: onPostBody");
});

// 	data-formatter

