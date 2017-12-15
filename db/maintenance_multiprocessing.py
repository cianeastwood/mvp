from scraper import ystockquote, snp500
from vola.models import Company, Stock, SNP500, Portfolio, Past_Portfolio, Past_Statistics
from datetime import datetime, timedelta
from db import access as dba, stockInserter
from vola import portfolioCalculator
from bulk_update.helper import bulk_update
import time, os, multiprocessing as mp
from django.db import connection

'''This module provides functions to keep the database up to date.'''

directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), "textfiles/")
recently_ceased_companies = os.path.join(directory, "ceased.txt")
results = []
past_results = []

def update_stocks(companies):
  ''' Updates stocks for given companies.

  :param companies: A list of company objects to update.

  :returns: A pair containing total stocks updated and companies updated.
  '''
  start_time = time.time()
  yday = datetime.today().date() - timedelta(days=1)
  cut_off_date = datetime.today().date() - timedelta(days=360) #no data in the last 2 months
  bulklist, not_updated = init_pool_stocks(companies, multi_processing_stocks, yday, cut_off_date)
  bulklist = [x for x in bulklist if x is not None]
  bulklist = [item for sublist in bulklist for item in sublist] #collapse list
  bulklist.extend(manual_update_ACE())
  not_updated = [x for x in not_updated if x is not None]
  if len(bulklist) == 0:
    return None, None
  stockInserter.insert_and_log_stocks(bulklist, len(companies) - len(not_updated), "previous latest", "yesterday", not_updated)
  print("--- %s seconds ---" % (time.time() - start_time))
  return len(bulklist), len(companies)

def init_pool_stocks(cs, funct, yday, date):
  num = len(cs)
  manager = mp.Manager() #results, past results
  results = manager.list([None]*num)
  past_results = manager.list([None]*num)
  pool = mp.Pool(processes=50) #os scheduling saves time due to http request delays
  for i, c in enumerate(cs):
    pool.apply_async(funct, args=[i, c, yday, date, results, past_results])
  pool.close()
  pool.join()
  return results, past_results

def multi_processing_stocks(i, c, yday, cut_off_date, results, past_results):
  connection.close()
  start_date = get_most_recent_date(c.symbol)
  if not start_date:
    past_results[i] = c.symbol
    return None
  if (start_date == yday) or (start_date < cut_off_date):
    past_results[i] = c.symbol
    return None
  yday = str(yday).replace("-","") #ystockquote date format
  start_date = str(start_date).replace("-","")
  hist_prices = ystockquote.get_historical_prices(c.symbol, start_date, yday)
  if not hist_prices: #http error / no stock hist for specified dates
    past_results[i] = c.symbol
    return None
  results[i] = stockInserter.create_stock_objects(hist_prices, c)

def multi_processing_recent_stocks(i, c, yday, last_update, results, past_results):
  connection.close()
  hist_prices = ystockquote.get_historical_prices(c.symbol, last_update, yday)
  if not hist_prices: #http error / no stock hist for specified dates
    past_results[i] = c.symbol
    return None
  results[i] = stockInserter.create_stock_objects(hist_prices, c)

def update_recent_admin(selected_companies): #recent SNP500 stocks only
  ''' Updates stocks for given companies.

  :param companies: A list of company objects to update.

  :returns: A pair containing total stocks updated and companies updated.
  '''
  indexes = get_indexes()
  current_companies = list(SNP500.objects.get(year=0).companies.all())
  this_year_companies = list(SNP500.objects.get(year=datetime.today().year).companies.all())
  last_year_companies = list(SNP500.objects.get(year=datetime.today().year -1).companies.all())
  SNP_companies = set(indexes + current_companies + this_year_companies + last_year_companies)
  companies = SNP_companies.intersection(selected_companies)
  last_update = str(get_most_recent_date('KO')).replace("-","") #Coca Cola as standard
  yday = str(datetime.today().date() - timedelta(days=1)).replace("-","")
  if last_update == yday:
    return None, None
  bulklist, not_updated = init_pool_stocks(companies, multi_processing_recent_stocks, yday, last_update)
  bulklist = [x for x in bulklist if x is not None]
  if len(bulklist) == 0:
    return None, None
  bulklist = [item for sublist in bulklist for item in sublist] #collapse list
  bulklist.extend(manual_update_ACE())
  not_updated = [x for x in not_updated if x is not None]
  stockInserter.insert_and_log_stocks(bulklist, len(companies) - len(not_updated), "previous latest", "yesterday", not_updated)
  return len(bulklist), len(companies)

def update_current_SNP500(current_snp):
  ''' Updates current S&P 500 constituents.

  :param current_snp: A SNP500 object with year=0 (current).

  :returns: A triple containing total companies added, removed and a boolean indicating new company data was available.
  '''
  current_snp_companies = current_snp.companies.all()
  current_snp_symbols = [c.symbol for c in current_snp_companies]
  wiki_data = snp500.get_current_consituents()
  wiki_symbols = [row[0] for row in wiki_data]
  added = [x for x in wiki_symbols if x not in current_snp_symbols]
  print(added)
  if added is None:
    return None, None
  companies = Company.objects.filter(symbol__in=wiki_symbols) #exsiting companies
  new_company_data = True
  if len(companies) != len(wiki_symbols): #new company
    company_symbols = companies.values_list('symbol', flat=True)
    missing_symbols = [x for x in added if x not in company_symbols]
    missing_company_data = [x for x in wiki_data if x[0] in missing_symbols]
    new_companies = add_new_companies(missing_company_data)
    prices_inserted = update_recently_added(new_companies)
    if prices_inserted == 0:
      new_company_data = False
    companies = list(companies) + new_companies #add to new companies list
  current_snp.companies = companies
  current_snp.save()
  added_companies = [company.name for company in companies if company.symbol in added]
  removed_companies = [company.name for company in current_snp_companies if company.symbol not in wiki_symbols]
  return added_companies, removed_companies, new_company_data

def update_recently_added(companies):
  ''' Updates stocks for given companies since 1988.

  :param companies: A list of company objects to update.

  :returns: An integer indicating the number of stocks added.
  '''
  bulklist = []
  not_updated = []
  yday = str(datetime.today().date() - timedelta(days=1)).replace("-","")
  for c in companies:
    start_date = '19880101'
    hist_prices = ystockquote.get_historical_prices(c.symbol, start_date, yday)
    if not hist_prices: #http error / no stock hist for specified dates
      not_updated.append(c.symbol)
      continue
    bulklist.extend(stockInserter.create_stock_objects(hist_prices, c))
  stockInserter.insert_and_log_stocks(bulklist, len(companies) - len(not_updated), "previous latest", "yesterday", not_updated)
  return len(bulklist)

def update_portfolio_calculations(portfolios):
  ''' Updates calculations for given portfolios.

  :param portfolios: A list of portfolio objects to update.
  '''
  start_time = time.time()
  portfolios, past_results = init_pool(portfolios, multi_processing_portfolios)
  past_portfolios = [item for sublist in past_results for item in sublist] #collapse list
  bulk_update(portfolios, update_fields=['symbols_field', 'allocations_field', 'vol', 'date_calculated'])
  bulk_update(past_portfolios, update_fields=['start_date', 'allocations_field', 'symbols_field'])
  print("--- %s seconds ---" % (time.time() - start_time))

def update_portfolio_performances(plots):
  ''' Updates calculations for given plots.

  :param portfolios: A list of plot objects to update.
  '''
  start_time = time.time()
  altered_plots, past_results = init_pool(plots, multi_processing_performances)
  past_stats = [item for sublist in past_results for item in sublist] #collapse list
  bulk_update(altered_plots, update_fields=['html'])
  bulk_update(past_stats, update_fields=['vol', 'ret', 'snp_vol', 'snp_ret', 'snp_lv_vol', 'snp_lv_ret', 'sharpe_ratio'])
  print("--- %s seconds ---" % (time.time() - start_time))

def init_pool(ps, funct):
  num = len(ps)
  manager = mp.Manager() #results, past results
  results = manager.list([None]*num)
  past_results = manager.list([None]*num)
  cores = mp.cpu_count()
  pool = mp.Pool(processes=cores)
  for i, p in enumerate(ps):
    pool.apply_async(funct, args=[i, p, results, past_results])
  pool.close()
  pool.join()
  return results, past_results

def multi_processing_portfolios(i, p, results, past_results):
  connection.close()
  today = datetime.today().date()
  p_updated = portfolioCalculator.update_or_create_portfolio(p.spread, p.period, p.lv, today, p=p)
  results[i] = p_updated
  past_results[i] = portfolioCalculator.update_past_portfolios(p_updated, today)

def multi_processing_performances(i, p, results, past_results):
  connection.close()
  ps, plot = portfolioCalculator.calculate_past_portfolio_performance(p.investment, p.portfolio, p)
  results[i] = plot
  past_results[i] = ps

def select_suggested_portfolio(p):
  ''' Marks given portfolio as suggested.

  :param p: A portfolio object.

  :returns: A boolean indicating updated or not.
  '''
  if p.suggested: #already selected
    return False
  else:
    Portfolio.objects.all().update(suggested=False)
    p.suggested = True
    p.save()
    return True

def add_new_companies(company_data):
  added = []
  for c_data in company_data:
    c = Company(symbol=c_data[0],name=c_data[1],sector=c_data[3],sub_industry=c_data[4],hq_address=c_data[5])
    c.save() #must be done individually for immediate save, cannot be bulk created
    added.append(c)
  return added

def log_ceased_symbols():
  #update_stocks() must have been run in the last 10 days
  last_update = 10
  ceased = []
  today = datetime.today()
  last_year = today.year 
  symbols = dba.get_SNP500_companies(last_year)
  recent_date = today.date() - timedelta(days=last_update)
  for s in symbols:
    start_date = get_most_recent_date(s)
    if not start_date:
      continue
    if start_date < recent_date:
      ceased.append(s)
  logfile = open(recently_ceased_companies, 'a')
  logfile.write("\n\nDate: {0}\n{1} SNP500 companies that have ceased this year: {2}".format(today, last_year, ceased))
  logfile.close()

def get_most_recent_date(symbol):
    try:
        stk = Stock.objects.filter(company__symbol=symbol).latest()
    except Stock.DoesNotExist:
        return '1988101' #when new symbols added
    return stk.date

def log_fully_available_symbols():
  start_time = time.time()
  logfile = open('db/textfiles/fully_avail_SNP_new.txt', 'a')
  for period in range(1,13): 
    print(period)
    logfile.write("\nMinimization period = " + str(period) + ": ")
    for year in range(2000, 2017):
      end = datetime.strptime(str(year) + "0101", '%Y%m%d').date()
      start = end - timedelta(days=365*period)
      symbols_available = len(dba.get_valid_symbols(start, end))
      logfile.write(str(symbols_available) + "\t")
      #print(str(period) + ":" + str(year) + ":" + str(cal_p_vol(str(year) + "0101", period, 100000)))
  logfile.write("--- %s seconds ---" % (time.time() - start_time))
  logfile.close()

def get_indexes():
  indexes = ["^GSPC", "SPLV"]
  return list(Company.objects.filter(symbol__in=indexes))

def manual_update_ACE():
  #Now CB, same price for multiple dates during merger/takeover - no conversion needed
  bulklist = []
  old_symbol = 'ACE'
  new_symbol = 'CB'
  company = Company.objects.get(symbol=old_symbol) 
  yday = datetime.today().date() - timedelta(days=1)
  start_date = get_most_recent_date(old_symbol)
  yday = str(yday).replace("-","") #ystockquote date format
  start_date = str(start_date).replace("-","")
  hist_prices = ystockquote.get_historical_prices(new_symbol, start_date, yday)
  if not hist_prices:
    return []
  return stockInserter.create_stock_objects(hist_prices, company)