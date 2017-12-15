import db.access as dba
import numpy as np
from decimal import Decimal
from vola.models import Stock

'''
This module provides functions to analyze a portfolio. 
Includes performance simulation against benchmarks and statistics calculation.
'''

def simulate(start, end, symbols, allocations, p_investment, b_investment, blv_investment=False, real=False):
    ''' Calculates the simulated performance of a portfolio.

    :param start: A date object indicating the start of the period to be analysed.
    :param end: A date object indicating the end of the period to be analysed.
    :param symbols: An ordered list of ticker symbols for the companies in the portfolio.
    :param allocations: An ordered list of allocations corresponding to ticker symbols in the symbols parameter.
    :param p_investment: A positive integer investment for the portfolio.
    :param b_investment: A positive integer investment for S&P 500 Index.
    :param blv_investment (optional): A positive integer investment for S&P 500 Low Volatility Index. Only available from 2012.
    :param real (optional): A boolean indication whether or not to use real-valued allocations, i.e. not round to integer shares.

    :returns A 4-tuple containing the performance statistics (dict), daily values (list), daily returns (list) and dates (list).
    '''
    p_prices = getPrices(start, end, symbols)
    dates = dba.get_valid_dates(start, end)
    changes = getChanges(start, end, symbols) #daily portfilio % changes
    b_changes = dba.SP500TR(start, end, 'change')
    b_prices = dba.SP500TR(start, end, 'close_price')
    if real:
        shares = (allocations * p_investment) / p_prices[0]
    else:
        shares = np.rint((allocations * p_investment) / p_prices[0])
    if blv_investment:
        blv_changes = dba.SP500LV(start, end, 'change')
        blv_prices = dba.SP500LV(start, end, 'close_price')
    else:
        blv_changes, blv_prices = [],[]
    stats, p_daily, b_daily, blv_daily = calcStats(p_investment, p_prices, changes, shares, b_prices, b_changes, b_investment, blv_changes, blv_prices, blv_investment)
    return stats, [p_daily, b_daily, blv_daily], [changes, b_changes, blv_changes], dates

def calc_stats_params(start, end, symbols, shares):
    ''' Calculates annual statistics for the given period, symbols and shares.

    :param start: A date object indicating the start of the period to be analysed.
    :param end: A date object indicating the end of the period to be analysed.
    :param symbols: An ordered list of ticker symbols for the companies in the portfolio.
    :param shares: An ordered list of shares corresponding to ticker symbols in the symbols parameter.

    :returns: A triple of decimals containing the volatility, return, and risk-adjusted return for the given parameters.
    '''
    prices = getPrices(start, end, symbols)
    changes = getChanges(start, end, symbols)
    vol = np.std(changes.dot(shares) / sum(shares))
    ret = (prices[-1].dot(shares) - prices[0].dot(shares)) / prices[0].dot(shares)
    risk_adj = ret / vol
    return vol, ret, risk_adj

def calcStats(p_investment, p_prices, indiv_changes, shares, b_prices, b_changes, b_investment, blv_changes, blv_prices, blv_investment):
    stats = {}  
    p_return = 100 * (p_prices[-1].dot(shares) - p_prices[0].dot(shares)) / p_prices[0].dot(shares)
    p_daily_returns = (indiv_changes.dot(shares) / sum(shares)) 
    p_daily_values = p_prices.dot(shares) 
    p_daily_values = p_daily_values + (p_investment - p_daily_values[0]) #pot left over from rounding
    b_return = 100 * ((b_prices[-1] - b_prices[0]) / b_prices[0]) #normalized $1
    b_daily_returns = b_changes 
    b_daily_values = b_prices * np.floor(b_investment / b_prices[0]) #normalized $1
    b_daily_values = b_daily_values + (b_investment - b_daily_values[0])
    sqrt_trading_days = np.sqrt(np.size(b_prices)) #annualize
    excess_returns = p_daily_returns - b_daily_returns 
    stats['volatility'] = round(np.std(indiv_changes.dot(shares) / sum(shares)) * sqrt_trading_days, 2)
    stats['return'] = round(p_return, 2)
    stats['sharpe'] = round((np.mean(excess_returns) / np.std(excess_returns)) * sqrt_trading_days, 2)
    stats['benchmark volatility'] = round((np.std(b_changes)*sqrt_trading_days).astype(Decimal), 2)
    stats['benchmark return'] = round(b_return.astype(Decimal), 2)
    blv_daily_values = []
    if blv_investment:
        blv_return = 100 * ((blv_prices[-1] - blv_prices[0]) / blv_prices[0]) 
        blv_daily_values = blv_prices * np.floor(blv_investment / blv_prices[0])
        blv_daily_values = blv_daily_values + (blv_investment - blv_daily_values[0])
        blv_daily_returns = blv_changes
        stats['benchmarklv volatility'] = round((np.std(blv_changes)*sqrt_trading_days).astype(Decimal), 2)
        stats['benchmarklv return'] = round(blv_return.astype(Decimal), 2)
    return stats, p_daily_values, b_daily_values, blv_daily_values

def getChanges(start, end, symbols):
    return dba.get_stock_matrix(start, end, symbols, 'change')

def getPrices(start, end, symbols):
    return dba.get_stock_matrix(start, end, symbols, 'close_price')