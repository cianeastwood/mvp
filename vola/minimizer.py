from db import access as dba
import numpy as np
import scipy.optimize as scopt

'''This module provides functions to calculate the optimal shares that minimize the portfolio's volatility.'''

def calculate_portfolio(start, end, min_spread, symbols, investment=None, live_prices=False):
  ''' Calculates the optimal shares that minimize the portfolio's volatility.

  :param start: A date object indicating the start of the period over which the volatility is to be minimised.
  :param end: A date object indicating the end of the period over which the volatility is to be minimised.
  :param min_spread: A positive integer
  :param symbols: A list of ticker symbols corresponding to the companies availble for minimisation.
  :param investment(optional): A positive integer representing the investment.
  :param live_prices(optional): A boolean indicating that live prices from Yahoo Finance should be used (if end date is today). Otherwise adjusted-close at end date is used.

  :returns: If investment given, a 4-tuple containing the shares(list), symbols(list), prices(list) and volatility(decimal). 
  If investment not given, a triple containing the allocations(list), symbols(list) and volatility(decimal).
  '''
  changes = dba.get_stock_matrix(start, end, symbols, 'change')
  allocations = minimize(vol, changes, investment, min_spread)
  allocations = set_effective_zero(allocations)
  trading_days = len(changes)
  if not investment:
    allocations, symbols, nz = filter_unused(allocations, symbols)
    min_vol = vol(allocations, changes[:,nz])
    return allocations, symbols, vol_annualized(min_vol, trading_days)
  shares, prices = get_shares_and_prices(end, symbols, allocations, investment, live_prices)
  shares, symbols, nz = filter_unused(shares, symbols)
  min_vol = vol_shares(shares, changes[:,nz])
  return shares, symbols, prices[nz], round(vol_annualized(min_vol, trading_days), 2)

def get_shares_and_prices(end, symbols, allocations, investment, live_prices=False):
  ''' Calculates annual statistics for the given period, symbols and shares.

  :param end: A date object indicating the end of the period over which the volatility is to be minimised.
  :param symbols: A list of ticker symbols corresponding to the companies availble for minimisation.
  :param shares: An ordered list of shares corresponding to ticker symbols in the symbols parameter.
  :param investment: A positive integer representing the investment.
  :param live_prices(optional): A boolean indicating that live prices from Yahoo Finance should be used (if end date is today). Otherwise adjusted-close at end date is used.

  :returns A pair containing the shares(integer list) and prices(list).
  '''
  prices = dba.get_prices(end, symbols, allocations, investment, live_prices)
  shares = np.rint((allocations * investment) / prices)
  return shares.astype(int), prices

def minimize(vol, changes, investment, min_spread):
    no_symbols = len(changes[0])
    max_investment = 1./min_spread #in a single company
    bounds = [(0., max_investment) for i in np.arange(no_symbols)] #non-negative weights 
    weights = np.ones(no_symbols)/no_symbols
    constraints = ({'type': 'eq',
                    'fun': lambda weights: np.sum(weights) - 1}) #sum of weights to equal 100%
    results = scopt.minimize(vol, weights, 
                                 method='SLSQP',
                                 constraints = constraints,
                                 bounds = bounds,
                                 args=changes)
    return np.array(results.x)

def vol(weights, changes):
    return np.std(changes.dot(weights))

def vol_shares(shares, changes):
  return np.std(changes.dot(shares) / sum(shares))

def vol_annualized(vol, trading_days):
  return vol*np.sqrt(trading_days)

def filter_unused(allocations, symbols):
    nz = np.flatnonzero(allocations)
    symbols = np.array(sorted(symbols))
    return allocations[nz], list(symbols[nz]), nz

def set_effective_zero(allocations):
    allocations[allocations < 1e-8] = 0 #investment < 100m will round down
    return allocations 