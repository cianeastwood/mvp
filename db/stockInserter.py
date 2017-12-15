from vola.models import Company, Stock
from decimal import Decimal
from datetime import datetime
import os

'''This modules provides functions to insert and log stock objects.'''

directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), "textfiles/")
log = os.path.join(directory, "log.txt")

def create_stock_objects(hist_prices, c):
  bulklist = []
  prices_asc = hist_prices[::-1] # reverse order (start date -> end date)
  prev_adj_close = Decimal(prices_asc[0][6]) #closing price earliest date (non inclusive)
  # skip last entry: [Date, Open, High, Low, Close, Volume, Adj Close]
  for i,day_data in enumerate(prices_asc[1:-1]):
    close_price = Decimal(day_data[6])
    if prev_adj_close == 0:
      change = close_price
    else:
      change = Decimal(((close_price - prev_adj_close)*100) / prev_adj_close)
    date = datetime.strptime(day_data[0], '%Y-%m-%d').date()
    bulklist.append(Stock(company=c, close_price=close_price, change=change, date=date))
    prev_adj_close = close_price
  return bulklist

def insert_and_log_stocks(bulklist, total_symbols, start_date, end_date, not_added):
  Stock.objects.bulk_create(bulklist)
  obj_inserted = len(bulklist)
  logfile = open(log, 'a')
  logfile.write(
    "\n\nDate: {0}\nInserted historical stocks from {1} to {2}\nTotal Stocks Added: {3}\nTotal Entries: {4}\nNot added: {5}".format(
    datetime.now(),start_date, end_date, total_symbols, obj_inserted, not_added))