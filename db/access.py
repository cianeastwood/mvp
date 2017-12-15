from vola.models import Company, Stock, SNP500, Portfolio, Past_Portfolio, Past_Statistics, Plot
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
from scraper import ystockquote

'''This module provides common database access functions.'''

def get_stock_matrix(start, end, symbols, value):
  ''' Retreives stock matrix for the given period, symbols and value.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.
  :param symbols: A list of ticker symbols for the companies in the portfolio.
  :param value: A string indicating the value to retrieve, e.g. close_price.

  :returns: A numpy array of floats.
  '''
  values = Stock.objects.filter(
    company__symbol__in=symbols, date__gte=start, date__lte=end).values_list(value, flat=True).order_by('date', 'company__symbol')
  num_symbols, num_entries = len(symbols), len(values)  
  total_dates = int(num_entries / num_symbols)
  if num_entries % num_symbols != 0: #Inconsistent dates
      ds= get_dates_to_exclude(start, end, symbols, value)
      print("Inconsistent")
      if not ds: #Error
        print("Error ", num_entries, num_symbols)
        return None
      else:
        #Stock.objects.filter(date__in=ds).delete() #remove inconsistent dates for future calculations
        values = Stock.objects.filter(company__symbol__in=symbols, date__gte=start, date__lte=end).exclude(date__in=ds).values_list(value, flat=True).order_by('date', 'company__symbol')
        num_entries = len(values)
  total_dates = int(num_entries / num_symbols)
  a = np.array(values, dtype=np.float32)
  a.shape = (total_dates, num_symbols)
  return a

def get_stock_matrixd(start, end, symbols, value):
  ''' Retreives stock matrix for the given period, symbols and value.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.
  :param symbols: A list of ticker symbols for the companies in the portfolio.
  :param value: A string indicating the value to retrieve, e.g. close_price.

  :returns: A numpy array of the same type as value.
  '''
  values = Stock.objects.filter(
    company__symbol__in=symbols, date__gte=start, date__lte=end).values_list(value, flat=True).order_by('date', 'company__symbol')
  num_symbols, num_entries = len(symbols), len(values)  
  total_dates = num_entries / num_symbols
  a = np.array(values)
  a.shape = (total_dates, num_symbols)
  return a

def SP500(start, end, value):
  ''' Retreives S&P 500 stock matrix for the given period and value.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.
  :param value: A string indicating the value to retrieve, e.g. close_price.

  :returns: A numpy array of floats.
  '''
  s = '^GSPC'
  values = Stock.objects.filter(company__symbol=s, date__gte=start, date__lte=end).values_list(value, flat=True).order_by('date')
  return np.array(values, dtype=np.float32)

def SP500TR(start, end, value):
  ''' Retreives S&P 500 stock matrix for the given period and value.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.
  :param value: A string indicating the value to retrieve, e.g. close_price.

  :returns: A numpy array of floats.
  '''
  s = '^SP500TR'
  values = Stock.objects.filter(company__symbol=s, date__gte=start, date__lte=end).values_list(value, flat=True).order_by('date')
  return np.array(values, dtype=np.float32)  

def SP500LV(start, end, value):
  ''' Retreives S&P 500 LV stock matrix for the given period and value.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.
  :param value: A string indicating the value to retrieve, e.g. close_price.

  :returns: A numpy array of floats.
  '''
  s = 'SPLV'
  values = Stock.objects.filter(company__symbol=s, date__gte=start, date__lte=end).values_list(value, flat=True).order_by('date')
  return np.array(values, dtype=np.float32)

#Valid symbols methods need to ensure:
# 1) Symbols were all available for the same number of trading days (no company just started etc.)
# 2) Symbols were all available on the same trading days (to get daily portfolio change)
def get_valid_symbols(start, end, current=False, perf=False):
  ''' Retreives valid symbols for given period.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.
  :param current(optional): A boolean indicating to use current S&P 500 list rather than historical.
  :param perf(optional): A boolean indicating performance testing (rather than minimisation).

  :returns: A sorted list of valid ticker symbols.
  '''
  if current:
    snp = get_SNP500_companies(0) #0 indicates current SNP500 constituents
  elif perf:
    snp = get_SNP500_companies(int(start.year)) #start of performance period, i.e. SNP500 symbols when investing
  else:
    snp = get_SNP500_companies(int(end.year)) #end of minimisation period, i.e. SNP500 symbols when investing
  valid_dates = get_valid_dates(start, end)
  syms = Stock.objects.filter(company__symbol__in=snp, date__gte=start, date__lte=end, date__in=valid_dates).values_list('company__symbol')
  s = Counter(syms) #symbols
  mc_s = s.most_common()
  num_trading_days = mc_s[0][1]
  return sorted([x[0][0] for x in mc_s if x[1]==num_trading_days])

def get_valid_symbols_check(start, end): #above method faster but not always consistent - double check required
  ''' Retreives symbols that are definately valid for given period (consistent but not efficent).

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.

  :returns: A sorted list of valid ticker symbols.
  '''
  year  = int(end.year) #end of minimisation period, i.e. SNP500 symbols when investing
  snp = SNP500.objects.filter(year=year).values_list('companies__symbol',flat=True) #SNP stocks for that year
  syms_n_dates = Stock.objects.filter(company__symbol__in=snp, date__gte=start, date__lte=end).values_list('company__symbol', 'date')
  s = Counter([x[0] for x in syms_n_dates]) #symbols
  mc_s = s.most_common()
  cm = Counter([x[1] for x in mc_s])
  mode = cm.most_common(1)[0][0] #find most common number of trading days, i.e. mode
  filtered_syms = [x[0]  for x in mc_s if x[1] == mode]
  filtered_syms_n_dates = [x for x in syms_n_dates if x[0] in filtered_syms]
  d = Counter([x[1] for x in filtered_syms_n_dates]) #dates
  mc_d = d.most_common() # find mode number of most common dates
  mc_d_least = mc_d[-1][1]
  mc_d_most = mc_d[0][1]
  if mc_d_most == mc_d_least: #if consistent dates already, return symbols
    return sorted(filtered_syms)
  dates_to_remove = [x[0] for x in mc_d if x[1] == mc_d_least]
  syms_to_remove = list(set([x[0] for x in filtered_syms_n_dates if x[1] in dates_to_remove]))
  return sorted([x for x in filtered_syms if x not in syms_to_remove])

def get_lowest_100_vol(symbols, end):
  ''' Calculates the 100 symbols with lowest volatility over the past year.

  :param symbols: A list of ticker symbols.
  :param end: A date object indicating the end of the period to be analysed.
  :param current(optional): Use current S&P 500 list rather than historical.

  :returns: A sorted list of 100 low volatility ticker symbols.
  '''
  symbols = sorted(symbols) # ensure sorted for zip
  changes = get_stock_matrix(end - timedelta(days=365), end, symbols, 'change')
  s = np.std(changes, axis=0)
  z = list(zip(symbols, s))
  z_sorted = sorted(z, key=lambda tup: tup[1])
  return [tup[0] for tup in z_sorted[:100]]

def get_valid_dates(start, end, sym='KO'):
  ''' Retreives valid dates for given period.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.

  :returns: A list of date objects.
  '''
  return Stock.objects.filter(company__symbol=sym, date__gte=start, date__lte=end).values_list('date', flat=True).order_by('date')

def get_SNP500_companies(year):
  ''' Retreives companies included in the S&P 500 list for a given year.

  :param year: An integer indicating the year.

  :returns: A list of ticker symbols.
  '''
  return SNP500.objects.filter(year=year).values_list('companies__symbol',flat=True) #SNP stocks for that year

def get_company_data(symbols):
  ''' Retreives company data for given symbols.

  :param symbols: A list of ticker symbols.

  :returns: A list of 4-tuples containing company data.
  '''
  companies = Company.objects.filter(symbol__in=symbols).order_by('symbol')
  data = [(c.name, c.sector, c.sub_industry, c.hq_address) for c in companies]
  return data

def get_prices(end, symbols, allocations, investment,live):
  ''' Retreives companies included in the S&P 500 list for a given year.

  :param end: A date object indicating the end of the period to be analysed.
  :param symbols: A list of ticker symbols.
  :param allocations: A numpy array of share allocations.
  :param investment: A positive integer.
  :param live: A boolean indicating whether or not to use live prices.

  :returns: A numpy float array of prices.
  '''
  if not live:
    return get_stock_matrix(end - timedelta(days=5), end, symbols, 'close_price')[0] #most recent prices
  min_share_price = 1 #better value?
  p_needed = allocations*investment >= min_share_price # only retreive the required prices
  s = np.array(symbols)
  symbols_needed = s[p_needed]
  p = ystockquote.get_multiple_prices(symbols_needed)
  p = p.split('\n')
  p = np.array([float(x) for x in p])
  if not np.all(p > 0):
    print("Error retreiving required live prices")
    return get_stock_matrix(end - timedelta(days=5), end, symbols, 'close_price')[0] #most recent prices
  else:
    prices = np.ones(len(symbols))*(investment*3) #rounds down when dividing into share allocations
    prices[p_needed] = p
    return prices 

def get_symbols_performance(start, end, lv, perf_test=False, current=False):
  ''' Retreives valid symbols when performance testing.

  :param start: A date object indicating the start of the period to be analysed.
  :param end: A date object indicating the end of the period to be analysed.
  :param lv: A boolean indicating whether or not only use low volatility stocks.
  :param perf_test(optional): A boolean indicating whether or not symbols need to be valid over the following year.
  :param current(optional): A boolean indicating whether or not to use the current S&P 500 companies.

  :returns: A sorted list of ticker symbols.
  '''
  symbols = get_valid_symbols(start, end)
  #tried to avoid this, but mergers / aqusitions made impossible
  #some data is simply not available the following year, cannot use those symbols
  if perf_test:
      avail_next_year = get_valid_symbols(end, end + timedelta(days=365), perf=perf_test)
      symbols = list(set(symbols).intersection(avail_next_year))
  if lv:
    symbols = get_lowest_100_vol(symbols, end)
  return symbols

def get_investments():
  ''' Retreives stored investments.

  :returns: A sorted list of investments.
  '''
  p = Portfolio.objects.filter(title='Custom').first()
  plots = Plot.objects.filter(portfolio=p)
  return sorted([pl.investment for pl in plots])

def get_periods():
  ''' Retreives stored periods.

  :returns: A sorted list of periods.
  '''
  ps = Portfolio.objects.filter(title='Custom', spread=25, lv=True) #arbritary title, spread, lv (just need constants)
  return sorted([p.period for p in ps])

def get_spreads():
  ''' Retreives stored spreads.

  :returns: A sorted list of spreads.
  '''
  ps = Portfolio.objects.filter(title='Custom', period=1, lv=True)
  return sorted([p.spread for p in ps])

def get_suggested_portfolio_performance():
  ''' Retreives plot and statistics for suggested portfolio.

  :returns: A pair containing a html plot and zipped statistics.
  '''
  investment = 100000
  p = Portfolio.objects.get(suggested=True)
  return get_performance_data(p, investment)

def get_performance_data(p, investment):
  saved_plot = Plot.objects.filter(portfolio=p, investment=investment)
  if not saved_plot.exists():
      return None, None
  pp = Past_Portfolio.objects.filter(portfolio=p).order_by('start_date')
  plot = saved_plot.first()
  fig = plot.html
  ps = list(Past_Statistics.objects.filter(plot=plot, past_portfolio__in=pp).order_by('past_portfolio__start_date'))
  p_vols = [p.vol for p in ps]
  b_vols = [p.snp_vol for p in ps]
  blv_vols = [p.snp_lv_vol for p in ps]
  p_rets = [p.ret for p in ps]
  b_rets = [p.snp_ret for p in ps]
  blv_rets = [p.snp_lv_ret for p in ps]
  sharpes = [p.sharpe_ratio for p in ps]
  vols = list(zip(p_vols, b_vols, blv_vols))
  returns = list(zip(p_rets, b_rets, blv_rets))
  dates = [str(pp.start_date + timedelta(days=365)) for pp in pp] #already sorted by date
  stats = list(zip(dates, vols, returns, sharpes))
  return fig, stats

def get_most_recent_date(symbol):
    try:
        stk = Stock.objects.filter(company__symbol=symbol).latest()
    except Stock.DoesNotExist:
        return None #'1988101' #when new symbols added
    return stk.date

def get_dates_to_exclude(start, end, symbols, value):
  dates_to_exclude = []
  valid_syms = get_valid_symbols_check(start,end)
  problem_syms = [x for x in symbols if x not in valid_syms]
  valid_dates = get_valid_dates(start, end)
  for s in problem_syms:
    prob_dates = Stock.objects.filter(company__symbol=s, date__gte=start, date__lte=end).values_list('date', flat=True)
    if not [x for x in valid_dates if x not in prob_dates]:
      exclude = [x for x in prob_dates if x not in valid_dates]
      dates_to_exclude += exclude
    elif not [x for x in prob_dates if x not in valid_dates]:
      #company no longer available (normally merger/aquisiton - unlikely company collapses in year following its inclusion in SNP500)
      #manually investigated here - database updated with new company figures for remainder of the year (avoid repeating workaround with each query)
      #example: ACE -> CB around 15/01/2016
      print("Data no longer available for " + s + " - merger? aquisiton?")
      return None
    else:
      print("{0} is missing dates:{1}\n{0} has extra dates:{2}".format(s,[x for x in valid_dates if x not in prob_dates], [x for x in prob_dates if x not in valid_dates]))
  return list(set(dates_to_exclude))