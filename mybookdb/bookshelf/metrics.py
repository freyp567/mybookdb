# metrics exposed to prometheus

from prometheus_client import Counter, Histogram


books_count = Counter('books_count', 'number of books on bookshelf')
books_read_count = Counter('books_read_count', 'number of books read')

