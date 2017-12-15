from urllib import request, error
from http.cookiejar import CookieJar
# proxies = {'http': 'http://proxy1.cs.nuim.ie:3128/'}
# opener=request.URLopener(proxies)
opener=request.URLopener()
cj = CookieJar()
price_opener = request.build_opener(request.HTTPCookieProcessor(cj))

'''
This module provides an API for retrieving stock data from Yahoo Finance.
'''

def get_historical_prices(symbol, start_date, end_date):
    """ Get historical prices for the given ticker symbol.

    :params symbol: Ticker symbol for company (str).
    :params start_date: String format is 'YYYYMMDD'.
    :params end_date: String format is 'YYYYMMDD'.
   
    :returns: A nested list of historical prices.
    """
    url = 'http://ichart.yahoo.com/table.csv?s=%s&' % symbol + \
          'd=%s&' % (int(str(end_date)[4:6]) - 1) + \
          'e=%s&' % (int(str(end_date)[6:8])) + \
          'f=%s&' % (int(str(end_date)[0:4])) + \
          'g=d&' + \
          'a=%s&' % (int(str(start_date)[4:6]) - 1) + \
          'b=%s&' % (int(str(start_date)[6:8])) + \
          'c=%s&' % (int(str(start_date)[0:4])) + \
          'ignore=.csv'
    try:
        days = opener.open(url).readlines()
    except error.HTTPError: #symbol not available
        return []
    except OSError: #yahoo block connection (suspected ddos)
        return []
    data = [day[:-1].decode('utf-8').split(',') for day in days]
    return data

def get_price(symbol):
    ''' Retreives current price for given symbol from Yahoo Finance.

    :params symbol: Ticker symbol for company (str).

    :returns: Price (str).
    '''
    return __request(symbol, 'l1')

def get_multiple_prices(symbols):
    ''' Retreives current prices for given symbols from Yahoo Finance.

    :params symbols: Ticker symbols (list).

    :returns: Prices (float list).
    '''
    symbols = ','.join(symbols)
    return __request(symbols, 'l1')
 
def get_all(symbol):
    """ Get all available quote data for the given ticker symbol.

    :params symbol: Ticker symbol for company (str).
   
    :returns: A dictionary.
    """
    values = __request(symbol, 'l1c1va2xj1b4j4dyekjm3m4rr5p5p6s7').split(',')
    data = {}
    data['price'] = values[0]
    data['change'] = values[1]
    data['volume'] = values[2]
    data['avg_daily_volume'] = values[3]
    data['stock_exchange'] = values[4]
    data['market_cap'] = values[5]
    data['book_value'] = values[6]
    data['ebitda'] = values[7]
    data['dividend_per_share'] = values[8]
    data['dividend_yield'] = values[9]
    data['earnings_per_share'] = values[10]
    data['52_week_high'] = values[11]
    data['52_week_low'] = values[12]
    data['50day_moving_avg'] = values[13]
    data['200day_moving_avg'] = values[14]
    data['price_earnings_ratio'] = values[15]
    data['price_earnings_growth_ratio'] = values[16]
    data['price_sales_ratio'] = values[17]
    data['price_book_ratio'] = values[18]
    data['short_ratio'] = values[19]
    return data
   
def __request(symbol, stat):
    try:
        url = 'http://finance.yahoo.com/d/quotes.csv?s=%s&f=%s' % (symbol, stat)
    except error.HTTPError:
        return None
    return price_opener.open(url).read().decode('utf-8').strip().strip('"')

#---------------------------------------------------------------------

def get_change(symbol):
    return __request(symbol, 'c1')
   
    
def get_volume(symbol):
    return __request(symbol, 'v')
 
 
def get_avg_daily_volume(symbol):
    return __request(symbol, 'a2')
   
    
def get_stock_exchange(symbol):
    return __request(symbol, 'x')
   
    
def get_market_cap(symbol):
    return __request(symbol, 'j1')
  
   
def get_book_value(symbol):
    return __request(symbol, 'b4')
 
 
def get_ebitda(symbol):
    return __request(symbol, 'j4')
   
    
def get_dividend_per_share(symbol):
    return __request(symbol, 'd')
 
 
def get_dividend_yield(symbol):
    return __request(symbol, 'y')
   
    
def get_earnings_per_share(symbol):
    return __request(symbol, 'e')
 
 
def get_52_week_high(symbol):
    return __request(symbol, 'k')
   
    
def get_52_week_low(symbol):
    return __request(symbol, 'j')
 
 
def get_50day_moving_avg(symbol):
    return __request(symbol, 'm3')
   
    
def get_200day_moving_avg(symbol):
    return __request(symbol, 'm4')
   
    
def get_price_earnings_ratio(symbol):
    return __request(symbol, 'r')
 
 
def get_price_earnings_growth_ratio(symbol):
    return __request(symbol, 'r5')
 
 
def get_price_sales_ratio(symbol):
    return __request(symbol, 'p5')
   
    
def get_price_book_ratio(symbol):
    return __request(symbol, 'p6')
      
       
def get_short_ratio(symbol):
    return __request(symbol, 's7')