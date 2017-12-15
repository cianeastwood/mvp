from django.test import TestCase
from django.core.urlresolvers import reverse
from datetime import datetime, timedelta
from .models import *
from db import reconstruction, maintenance, access
import numpy as np
from . import minimizer, portfolioCalculator, portfolioAnalyzer

'''
This module provides automated tests for vola application.
'''

class CompanyPopulationTests(TestCase):
    def test_most_recent_price_available(self):
        """
        get_most_recent_price() should return the most recent price
        or None if no data is available for that Company.
        """
        c = Company(symbol='KO', name="Coca Cola")
        c.save()
       	self.assertEqual(c.get_most_recent_price(), None)
        today = datetime.today().date()
        s = Stock(company=c, close_price=100, change=1, date=today)
        s.save()
        self.assertEqual(c.get_most_recent_price(), 100)

    def test_company_population(self):
    	''' Company data should be inserted correctly from textfiles.'''
    	inserted = reconstruction.populate_companies()
    	check = Company.objects.all().count()
    	self.assertEqual(inserted, check)

    def test_company_population_2016(self):
     	""" Company data should be inserted correctly from textfiles."""
     	inserted = reconstruction.populate_companies_2016()
     	check = Company.objects.all().count()
     	self.assertEqual(inserted, check)
     	self.assertEqual(inserted, 504)

    def test_historical_company_population(self):
    	""" Company data should be inserted correctly from textfiles."""
    	inserted = reconstruction.populate_historial_companies()
    	check = Company.objects.all().count()
    	self.assertEqual(inserted, check)
    	self.assertEqual(inserted, 671)

class CompanyMethodTests(TestCase):
	fixtures = ['company.json']

	def test_get_company_data(self):
		''' Company data should be retreived with name first.'''
		data = access.get_company_data(['A'])[0]
		name = data[0]
		self.assertEqual(name, "Agilent Technologies Inc")

class StockMethodTests(TestCase):
	fixtures = ['company.json', 'stock.json', 'SNP500.json']

	def test_indexes(self):
		""" S&P 500 and S&P 500 LV Stocks should be returned."""
		start = datetime.today().date()
		end = start - timedelta(days=365)
		self.assertIsNotNone(access.SP500(start, end, 'change'))
		self.assertIsNotNone(access.SP500LV(start, end, 'change'))

	def test_valid_dates(self):
		""" get_valid_dates() should return at least one date in the last year for given fixtures."""
		start = datetime.today().date()
		end = start - timedelta(days=365)
		self.assertIsNotNone(access.get_valid_dates(start, end, sym='A'))

	def get_valid_symbols_check(self):
		""" get_valid_symbols_check() should return at least one valid symbol in the last year for given fixtures."""
		start = datetime.today().date()
		end = start - timedelta(days=30)
		syms = access.get_valid_symbols_check(start, end)
		self.assertNotEqual(syms, [])

	def test_update_stocks(self):
		""" update_stocks() should update at least 6 stocks updated for all 8 companies. """
		stocks, companies = maintenance.update_stocks(Company.objects.all())
		self.assertEqual(companies, 8)
		self.assertTrue(stocks > 6)

	def test_recently_added(self):
		""" update_recently_added() should update at least 1000 stocks for selected company. """
		stocks = maintenance.update_recently_added(Company.objects.filter(symbol="GOOGL"))
		self.assertTrue(stocks > 1000)

	def test_populate_stocks(self):
	    """ populate_stocks() should should insert at least one stock for each ccompany available in specified date range. """
	    end = datetime.today().date()
	    start = end - timedelta(days=5)
	    stocks_inserted = reconstruction.populate_stocks('20160315', '20160317')
	    self.assertTrue(stocks_inserted > 6)

	def test_filter_zero_prices(self):
	    """ filter_zero_prices() should not find any stocks with prices equal to zero. """
	    stocks = reconstruction.filter_zero_prices()
	    self.assertEqual(len(stocks), 0)

class SNP500MethodTests(TestCase):
	fixtures = ['company.json', 'stock.json', 'SNP500.json']

	def test_get_SNP500_companies(self):
		""" get_SNP500_companies() should return at least one company based on fixture SNP500.json. """
		s = access.get_SNP500_companies(0)
		self.assertTrue(len(s) > 0)

	#Takes a long time to complete - not run every time
	# def test_update_current_SNP500(self):
	# 	added, removed, new_company_data = maintenance.update_current_SNP500(SNP500.objects.get(year=0))
	# 	self.assertTrue(len(added) > 450)
	# 	self.assertIsNone(removed)
	# 	self.assertTrue(new_company_data)

	def test_populate_snp_2016(self):
		""" populate_snp_2016() should return the same companies as loaded from fixture. """
		old_comp = access.get_SNP500_companies(2016)
		new_comp = reconstruction.populate_snp_2016()
		self.assertTrue(len(new_comp) == len(old_comp))

class PortfolioMethodTests(TestCase):
	fixtures = ['company.json', 'stock.json', 'SNP500.json']		

	def test_minimizer(self):
	    """ 
	    minimizer() should always return non-empty shares, symbols and prices. 
	    Volatility should be zero for given stock fixtures. 
	    """
	    start = datetime.strptime('20160313', '%Y%m%d').date()
	    end = datetime.strptime('20160315', '%Y%m%d').date()
	    shares, symbols, prices, vol = minimizer.calculate_portfolio(start, end, 1, ['A', 'ACE', 'CB'], 100000, live_prices=False)
	    self.assertIsNotNone(shares)
	    self.assertIsNotNone(symbols)
	    self.assertIsNotNone(prices)
	    self.assertEqual(vol, 0)

	def test_portfolioCalculator(self):
		""" 
        update_or_create_portfolio() should always return a portfolio with minimisation volatility of 0.
        create_past_portfolios() should always return a past portfolio with non empty symbols and allocations.
        update_past_portfolios() should always return a past portfolio with non empty symbols and allocations.
        """
		end = datetime.strptime('20160316', '%Y%m%d').date()
		p = portfolioCalculator.update_or_create_portfolio(1, 1, True, end)
		p.save()
		self.assertEqual(p.vol, 0)
		pp = portfolioCalculator.create_past_portfolios(p, 2015, end)[0]
		self.assertIsNotNone(pp.symbols)
		self.assertIsNotNone(pp.allocations)
		pp.save()
		pp = portfolioCalculator.update_past_portfolios(p, end)[0]
		self.assertIsNotNone(pp.symbols)
		self.assertIsNotNone(pp.allocations)

	def test_portfolioAnalyzer(self):
		""" 
        portfolioAnalyzer.simulate() should always return:
        -Non empty dates, changes
        -Volatility of 0 for the portolio and both benchmarks for the given stock fixtures.
        """
		end = datetime.strptime('20160316', '%Y%m%d').date()
		start = datetime.strptime('20160312', '%Y%m%d').date()
		stats, values, changes, dates = portfolioAnalyzer.simulate(start, end, ['ACE', 'CB'], np.array([.5, .5]), 10000, 10000, 10000)
		self.assertIsNotNone(dates)
		self.assertIsNotNone(changes[0])
		self.assertEqual(stats['volatility'], 0)
		self.assertEqual(stats['benchmark volatility'], 0)
		self.assertEqual(stats['benchmarklv volatility'], 0)


class ViewTests(TestCase):

	def test_index_view(self):
		""" Static home page should be available without database. """
		response = self.client.get(reverse('vola:index'))
		self.assertEqual(response.status_code, 200)

	def test_about_view(self):
		""" Static about page should be available without database. """
		response = self.client.get(reverse('vola:about'))
		self.assertEqual(response.status_code, 200)