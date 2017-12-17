from scraper import ystockquote
from vola.models import Company, Stock, SNP500, Portfolio, Past_Portfolio, Past_Statistics, Plot
from datetime import datetime, timedelta
from db import access as dba, stockInserter
from vola import portfolioCalculator
from bulk_update.helper import bulk_update
import os
import django

'''
This module contains manual functions needed to reconstruct the database.

->population of stock data
->manual cleansing of data from Yahoo Finance
->population of historical S&P 500 lists
->population of portfolios
'''

directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), "textfiles/")

def populate_companies():
  bulklist = []
  txt = open(directory + 'symbols.txt')
  comp_data = [[sym for sym in line.split('\t')] for line in txt]
  for row in comp_data[1:]:
    bulklist.append(Company(symbol=row[0],name=row[1],sector=row[3],sub_industry=row[4],hq_address=row[5]))
  Company.objects.bulk_create(bulklist)
  return len(bulklist)

def populate_companies_2016():
  bulklist = []
  cur_symbols = Company.objects.all().values_list('symbol',flat=True)
  txt = open(directory + 'snp2016.txt')
  comp_data = [[sym for sym in line.split('\t')] for line in txt]
  count = 0
  for row in comp_data[1:]:
    if row[0] not in cur_symbols:
      bulklist.append(Company(symbol=row[0],name=row[1],sector=row[3],sub_industry=row[4],hq_address=row[5]))
      count +=1
  Company.objects.bulk_create(bulklist)
  return count

def populate_historial_companies():
  bulklist = []
  cur_symbols = Company.objects.all().values_list('symbol',flat=True)
  f = open(directory + 'availableSNP.csv')
  new_symbols = [y[:2] for y in [x.split(',') for x in f.read().splitlines()]]
  sym = [x for x in new_symbols[1:] if x[0] not in cur_symbols]
  for new_company in sym:
    bulklist.append(Company(symbol=new_company[0],name=new_company[1]))
  Company.objects.bulk_create(bulklist)
  return len(bulklist)

def create_SNP500_objs(years):
    snps = [SNP500(year=year) for year in years]
    SNP500.objects.bulk_create(snps)

def populate_hist_snp():
  f = open(directory + 'availableSNP.csv')
  info = [x.split(',') for x in f.read().splitlines()]
  years = [[] for _ in range(16)]
  for row in info:
    for i in range(2,18):
      if row[i] == "1":
        years[i-2].append(row[0])
  snps = SNP500.objects.all().order_by('year')
  snps = snps[::-1]
  companies = [Company.objects.filter(symbol__in=y) for y in years]
  for i, snp in enumerate(snps[1:]):
    snp.companies = companies[i]
    snp.save()
  return snps

def populate_snp_2016():
  txt = open(directory + "snp2016.txt")
  comp_data = [[sym for sym in line.split('\t')] for line in txt]
  syms = [row[0] for row in comp_data[1:]]
  syms.sort()
  companies = Company.objects.filter(symbol__in=syms)
  snp = SNP500.objects.get(year=2016)
  snp.companies = companies
  snp.save()
  return companies

def populate_stocks(start_date, end_date):
  ''' Date: String format 'YYYYMMDD' '''
  bulklist = []
  not_added = []
  companies = Company.objects.all()
  for c in companies:
    hist_prices = ystockquote.get_historical_prices(c.symbol, start_date, end_date)
    if not hist_prices: #http error / no stock hist for specified dates
      not_added.append(c.symbol)
      continue
    print(hist_prices)
    bulklist.extend(stockInserter.create_stock_objects(hist_prices, c))
  stockInserter.insert_and_log_stocks(bulklist, len(companies) - len(not_added), start_date, end_date, not_added)
  return len(bulklist)


def populate_custom_portfolios():
  today = datetime.today().date()
  periods = [1, 2, 4, 8, 12]
  spreads = [25, 50, 75, 100]
  lvs = [True, False]
  
  bulklist = []
  for lv in lvs:
    print(lv)
    for period in periods:
      print(period)
      for spread in spreads:
        print(spread)
        bulklist.append(portfolioCalculator.update_or_create_portfolio(spread, period, lv, today))
  Portfolio.objects.bulk_create(bulklist)

def select_suggested_portfolio():
  suggested_params = [50, 4, False] #spread, period, lv
  p = select_suggested_portfolio(*suggested_params)
  p.save()

def select_suggested_portfolio(spread, period, lv):
  p = Portfolio.objects.get(period=period, spread=spread, lv=lv)
  if not p.suggested:
    Portfolio.objects.all().update(suggested=False)
    p.suggested = True
    return p

def populate_past_portfolios():
  SNP500LV_start_year = 2012
  portfolios = Portfolio.objects.all()
  bulklist = []
  for p in portfolios:
    print(p.lv, p.period, p.spread)
    bulklist += portfolioCalculator.create_past_portfolios(p, SNP500LV_start_year, datetime.today().date())
  Past_Portfolio.objects.bulk_create(bulklist)

def populate_past_statistics_and_plot():
  investments = [10000, 25000, 50000, 100000, 250000, 1000000]
  portfolios = Portfolio.objects.all()
  past_stats = []
  plots = []
  for p in portfolios:
    print(p.lv, p.period, p.spread)
    for inv in investments:
      print(inv)
      ps, plot = portfolioCalculator.calculate_past_portfolio_performance(inv, p)
      past_stats += ps
      plots.append(plot)
  bulk_update(plots, update_fields=['html'])
  Past_Statistics.objects.bulk_create(past_stats)

# START: Remove dirty data from yahoo ------------------
def cleanse_BOL():
  start = datetime.strptime('20040101', '%Y%m%d').date()
  end = datetime.strptime('20041231', '%Y%m%d').date()
  a = Stock.objects.filter(company__symbol='A', date__gte=start, date__lte=end).values_list('date').order_by('date', 'company__symbol')
  bol = Stock.objects.filter(company__symbol='BOL', date__gte=start, date__lte=end).values_list('date').order_by('date', 'company__symbol')
  to_add = [x for x in a if x not in bol]
  to_remove = [x[0] for x in bol if x not in a]
  prev_days = [x[0] + timedelta(days=1) for x in to_add]
  prev_days_info = list(Stock.objects.filter(company__symbol='BOL', date__in=prev_days).values_list('date', 'close_price', 'change').order_by('date', 'company__symbol'))
  new_info = prev_days_info[-1]
  new_info = (new_info[0] - timedelta(days=1), new_info[1], new_info[2])
  prev_days_info.append(new_info)
  bulklist = []
  for i in prev_days_info:
    bulklist.append(Stock(company=Company.objects.get(symbol='BOL'), close_price=i[1], change=i[2], date=i[0] - timedelta(days=1)))
  # Stock.objects.filter(company__symbol='BOL', date__in=to_remove).delete()
  Stock.objects.bulk_create(bulklist)
  bol = Stock.objects.filter(company__symbol='BOL', date__gte=start, date__lte=end).values_list('date').order_by('date', 'company__symbol')
  print(len(bol))

def cleanse_others():
  start = datetime.strptime('20110101', '%Y%m%d').date()
  end = datetime.strptime('20111231', '%Y%m%d').date()
  a = Stock.objects.filter(company__symbol='A', date__gte=start, date__lte=end).values_list('date').order_by('date', 'company__symbol')
  nyx = Stock.objects.filter(company__symbol='NYX', date__gte=start, date__lte=end).values_list('date').order_by('date', 'company__symbol')
  to_remove = [x[0] for x in nyx if x not in a]
  Stock.objects.filter(company__symbol__in=['NYX', 'FRX', 'CPWR'], date__in=to_remove).delete()
  nyx = Stock.objects.filter(company__symbol='NYX', date__gte=start, date__lte=end).values_list('date').order_by('date', 'company__symbol')
  print(len(nyx))

def filter_zero_prices():
  ''' 17 companies with multiple prices == 0 '''
  remove = list(set(Stock.objects.filter(close_price=0).values_list('company__symbol', flat=True)))
  return remove

# END: Remove dirty data from yahoo ------------------

if __name__ == '__main__':
    # Set params
    start_date = '20000101'
    end_date = '20160301'
    snp_years = [y for y in range(int(start_date[:4]), int(end_date[:4]) + 1)]
    snp_years = snp_years
    django.setup()

    # Populate copmany, stock and S&P500 info
    populate_companies() # Create Company objects from txt file of company info
    populate_companies_2016() # Create Company objects for more recent companies (2016) - different txt file
    populate_historial_companies() # Recent companies in SNP not in prev txt files - create company objects (no descriptions)
    create_SNP500_objs(snp_years) # Stores list of symbols for each year
    populate_hist_snp() # Add snp companies to relevant snp list (one per year in range)
    populate_snp_2016() # Add snp companies to relevant snp list (one per year in range) - 2016 in different file
    populate_stocks(start_date, end_date) # Create stock objects and populate with stock info in desired range 'YYYYMMDD'

    # Remove dirty data from yahoo
    cleanse_BOL()
    cleanse_others()
    filter_zero_prices()

    # Pre-compute and store custom mvps and corresponding stats
    populate_custom_portfolios() # Pre-compute and store all possible custom portfolios for increased peformance
    select_suggested_portfolio() # Select suggested mvp params, i.e. spread, period, lv
    populate_past_portfolios() # Past portfolio = old portfolio with out-of-date end date... i.e. the is a more recent Portfolio object
    populate_past_statistics_and_plot() #Pre-compute and store portfolio stats at fixed-interval investments for increased peformance
