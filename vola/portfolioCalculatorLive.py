from vola import minimizer, portfolioAnalyzer
from db import access as dba
from datetime import datetime, timedelta
import matplotlib.pyplot as plt, mpld3
import matplotlib.dates as mdates
import numpy as np

'''
This module provides functions to live calculate custom portfolio performance.
Note that this module is not currently used in the web application.
'''

test_start = 2012 #LV benchmark started in 2012

def calculate_portfolio(investment, minimum_spread, lv, analyse_performance, live, period):
    ''' Calculates the custom portfolio and it's past performance live.
    May take up to two minutes when analysing performance for a large minimisation period.

    :param investment: A positive integer.
    :param minimum_spread: A positive integer <= 100.
    :param lv: A boolean. True indicates to only use the 100 lowest volatility stocks.
    :param analyse_performance: A boolean. True indicates to analyse past performance.
    :param period: A positive integer  <= 12 representing the minimisation period.
  
    :returns: A 4-tuple containing the zipped current portfolio data, amount actually invested (decimal), volatility (decimal), zipped statistics
    '''
    end = datetime.today().date()
    start = end - timedelta(days=365*period)
    symbols = get_symbols(start, end, lv)
    shares, symbols, prices, min_vol= minimizer.calculate_portfolio(start, end, minimum_spread, symbols, investment, live)
    investments = np.round(np.multiply(shares, prices), 2)
    invested = prices.dot(shares)
    company_data = dba.get_company_data(symbols)
    data = list(zip(company_data, prices, shares, investments))
    fig, stats = None, None
    if analyse_performance:
        fig, stats = performance_testing(investment, minimum_spread, end, lv, period)
    return data, invested, min_vol, fig, stats

def performance_testing(investment, minimum_spread, end, lv, period):
    annual_date = str(end.month) + str(end.day)
    day_before_investing = datetime.strptime(str(test_start) + annual_date, '%Y%m%d').date() - timedelta(days=2)
    p_daily_values = [investment]
    p_annual_vols = []
    p_annual_return = []
    b_daily_values = [investment]
    b_annual_vols = []
    b_annual_return = []
    blv_daily_values = [investment]
    blv_annual_vols = []
    blv_annual_return = []
    dates = [day_before_investing]
    sharpes = []
    for year in range(test_start, end.year):
        end = datetime.strptime(str(year)+ annual_date, '%Y%m%d').date() - timedelta(days=1) #performance up to yday
        start = end - timedelta(days=365*period)
        symbols = get_symbols(start, end, lv, True)
        allocations, symbols, vol = minimizer.calculate_portfolio(start, end, minimum_spread, symbols)
        stats, daily_values, daily_changes, ds = portfolioAnalyzer.simulate(end, end + timedelta(days=365), symbols, allocations, p_daily_values[-1], b_daily_values[-1], blv_daily_values[-1])
        p_daily_values += list(daily_values[0])
        p_annual_vols.append(stats['volatility'])
        p_annual_return.append(stats['return'])
        b_daily_values += list(daily_values[1])
        b_annual_vols.append(stats['benchmark volatility'])
        b_annual_return.append(stats['benchmark return'])
        dates += list(ds)
        blv_daily_values += list(daily_values[2])
        blv_annual_vols.append(stats['benchmarklv volatility'])
        blv_annual_return.append(stats['benchmarklv return'])
        sharpes.append(stats['sharpe'])
    fig = plot_graphs(p_daily_values, b_daily_values, blv_daily_values, dates)
    vols = list(zip(p_annual_vols, b_annual_vols, blv_annual_vols))
    returns = list(zip(p_annual_return, b_annual_return, blv_annual_return))
    years = list(range(test_start, end.year+1))
    ann_date =  str(end.day) + "/" + str(end.month) + "/"
    dates = [ann_date + str(year+1) for year in years]
    stats = list(zip(dates, vols, returns, sharpes))
    return fig, stats

#Problems with inconsistent data investing in 2012 until 2016 -  not implemented 
def performance_testing_hold(investment, minimum_spread, end, lv, period):
    annual_date = '0101'
    day_before_investing = datetime.strptime(str(test_start) + annual_date, '%Y%m%d').date() - timedelta(days=2)
    p_daily_values = [investment]
    b_daily_values = [investment]
    blv_daily_values = [investment]
    dates = [day_before_investing]
    end = datetime.strptime('20120101', '%Y%m%d').date()
    end_test = datetime.strptime('20160301', '%Y%m%d').date()
    start = end - timedelta(days=365*period)
    hold_period = (end_test - end).days 
    symbols = get_symbols(start, end, lv, True, hold_period)
    allocations, symbols, vol = minimizer.calculate_portfolio(start, end, minimum_spread, symbols)
    stats, daily_values, daily_changes, ds = portfolioAnalyzer.simulate(end, end_test, symbols, allocations, p_daily_values[-1], b_daily_values[-1], blv_daily_values[-1], True)
    p_daily_values += list(daily_values[0])
    p_annual_vols = [stats['volatility']]
    p_annual_return = [stats['return']]
    b_daily_values += list(daily_values[1])
    b_annual_vols = [stats['benchmark volatility']]
    b_annual_return = [stats['benchmark return']]
    dates += list(ds)
    blv_daily_values += list(daily_values[2])
    blv_annual_vols = [stats['benchmarklv volatility']]
    blv_annual_return = [stats['benchmarklv return']]
    sharpes = [stats['sharpe']]
    fig = plot_graphs(p_daily_values, b_daily_values, blv_daily_values, dates)
    vols = list(zip(p_annual_vols, b_annual_vols, blv_annual_vols))
    returns = list(zip(p_annual_return, b_annual_return, blv_annual_return))
    dates = [str(end_test)]
    stats = list(zip(dates, vols, returns, sharpes))
    return fig, stats

def plot_graphs(p_vals, b_vals, blv_vals, dates):
    years = mdates.YearLocator()
    months = mdates.MonthLocator()
    fig, ax = plt.subplots()
    ax.plot(dates, b_vals, color=(0,0,1), label="S&P 500", linewidth=1)
    ax.plot(dates, blv_vals, color=(0,1,0), label="S&P 500 LV", linewidth=1)
    ax.plot(dates, p_vals, color=(1,0,0), label="Your Portfolio", linewidth=1)
    # # format the ticks
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_minor_locator(months)
    ax.set_xlim(dates[0], dates[-1])
    # format the coords message box
    ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.format_ydata = price
    ax.grid(True)
    # rotates and right aligns the x labels, and moves the bottom of the
    # axes up to make room for them
    fig.autofmt_xdate()
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.title('Portfolio Performance vs Benchmarks')
    #(-0.01, 1.01) = top left (upper left)
    #(0.5, -0.07) = bottom center (upper center)
    plt.legend(loc='upper left', bbox_to_anchor=(-0.01, 1.01), ncol=3, fancybox=True, shadow=True, title="")
    #plt.savefig('vola/static/vola/graphs/annual_rebalance_real.png', dpi=150)
    fig_html = mpld3.fig_to_html(fig)
    return fig_html

def price(x):
    return '$%1.2f' % x

def get_symbols(start, end, lv, perf_test=False, rebal_period=1):
    symbols = dba.get_valid_symbols(start, end)
    #tried to avoid this, but mergers / aqusitions made impossible
    #some data is simply not available the following year, cannot use those symbols
    if perf_test:
        avail_next_year = dba.get_valid_symbols(end, end + timedelta(days=365*rebal_period))
        symbols = list(set(symbols).intersection(avail_next_year))
    if lv:
    	symbols = dba.get_lowest_100_vol(symbols, end)
    return symbols