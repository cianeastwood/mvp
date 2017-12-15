from vola import minimizer, portfolioAnalyzer
from vola.models import Portfolio, Past_Portfolio, Past_Statistics, Plot
from db import access as dba
from datetime import datetime, timedelta
import matplotlib.pyplot as plt, mpld3
import matplotlib.dates as mdates
import numpy as np

'''This module provides functions for retreiving, calculating and storing portfolios and their past performances.'''

def calculate_portfolio(investment, minimum_spread, lv, analyse_performance, live, period):
    ''' Calculates portfolio performance for given investment (retreives performance if stored).

    :param investment: A positive integer.
    :param minimum_spread: A positive integer <= 100.
    :param lv: A boolean. True indicates to only use the 100 lowest volatility stocks.
    :param analyse_performance: A boolean. True indicates to analyse past performance.
    :param period: A positive integer  <= 12 representing the minimisation period.
  
    :returns: A 4-tuple containing the zipped current portfolio data, amount actually invested (decimal), volatility (decimal), zipped statistics
    '''
    p = Portfolio.objects.get(title="Custom", spread=minimum_spread, period=period, lv=lv)
    #yday = datetime.today().date() - timedelta(days=1) #yday prices, if NOT live prices
    end = dba.get_most_recent_date('KO')
    print(end)
    shares, prices = minimizer.get_shares_and_prices(end, p.symbols, p.allocations, investment, live)
    data, invested = pack_formated_data(shares, prices, p.symbols)
    fig, stats = None, None
    if analyse_performance:
        fig, stats =dba.get_performance_data(p, investment)
        if fig is None: #investment not stored
            fig, stats = live_calculate_past_portfolio_performance(investment, p)
    return data, invested, p.vol, fig, stats

def calculate_past_portfolio_performance(investment, portfolio, plot=None):
    ''' Calculates the past performance of a portfolio.

    :param investment: A positive integert.
    :param portfolio: A Portfolio object for which to calculate the past performance.
    :param plot(optional):  A Plot object in which to save the plot for given investment. New plot created if not provided.

    :returns: A pair containing a list of Past_Portfolio objects to be saved in bulk and a Plot object for the given portfolio and investment.
    '''
    past_portfolios = list(Past_Portfolio.objects.filter(portfolio=portfolio).order_by('start_date'))
    if plot is None:
        plot = Plot(portfolio=portfolio, investment=investment)
        plot.save() #assign pk
    start_date = past_portfolios[0].start_date #initial start date
    day_before_investing = start_date - timedelta(days=1)
    p_daily_values = [investment]
    b_daily_values = [investment]
    blv_daily_values = [investment]
    dates = [day_before_investing]
    bulklist = []
    for pp in past_portfolios:
        stats, daily_values, daily_changes, ds = portfolioAnalyzer.simulate(pp.start_date, pp.start_date + timedelta(days=365), pp.symbols, pp.allocations, p_daily_values[-1], b_daily_values[-1], blv_daily_values[-1])
        p_daily_values += list(daily_values[0])
        b_daily_values += list(daily_values[1])
        blv_daily_values += list(daily_values[2])
        dates += list(ds)
        if plot is None:
            ps = Past_Statistics(past_portfolio=pp, plot=plot)
        else:
            ps = Past_Statistics.objects.get(past_portfolio=pp, plot=plot)
        ps.vol, ps.ret, ps.sharpe_ratio = stats['volatility'], stats['return'], stats['sharpe']
        ps.snp_vol, ps.snp_ret = stats['benchmark volatility'], stats['benchmark return']
        ps.snp_lv_vol, ps.snp_lv_ret = stats['benchmarklv volatility'], stats['benchmarklv return']
        bulklist.append(ps)
    fig = plot_graphs(p_daily_values, b_daily_values, blv_daily_values, dates)
    plot.html = fig
    return bulklist, plot

def live_calculate_past_portfolio_performance(investment, portfolio):
    ''' Calculates the past performance of a portfolio live.

    :param investment: A positive integer.
    :param portfolio: A Portfolio object for which to calculate the past performance.

    :returns: A pair containing a html performance plot and zipped annual statistics.
    '''
    past_portfolios = list(Past_Portfolio.objects.filter(portfolio=portfolio).order_by('start_date')) #must be ordered ascending
    start_date = past_portfolios[0].start_date #initial start date
    day_before_investing = start_date - timedelta(days=1)
    p_daily_values = [investment]
    b_daily_values = [investment]
    blv_daily_values = [investment]
    dates = [day_before_investing]
    p_annual_vols = []
    p_annual_return = []
    b_annual_vols = []
    b_annual_return = []
    blv_annual_vols = []
    blv_annual_return = []
    sharpes = []
    for pp in past_portfolios:
        stats, daily_values, daily_changes, ds = portfolioAnalyzer.simulate(pp.start_date, pp.start_date + timedelta(days=365), pp.symbols, pp.allocations, p_daily_values[-1], b_daily_values[-1], blv_daily_values[-1])
        p_daily_values += list(daily_values[0])
        b_daily_values += list(daily_values[1])
        blv_daily_values += list(daily_values[2])
        dates += list(ds)
        p_annual_vols.append(stats['volatility'])
        p_annual_return.append(stats['return'])
        b_annual_vols.append(stats['benchmark volatility'])
        b_annual_return.append(stats['benchmark return'])
        blv_annual_vols.append(stats['benchmarklv volatility'])
        blv_annual_return.append(stats['benchmarklv return'])
        sharpes.append(stats['sharpe'])
    fig = plot_graphs(p_daily_values, b_daily_values, blv_daily_values, dates)
    vols = list(zip(p_annual_vols, b_annual_vols, blv_annual_vols))
    returns = list(zip(p_annual_return, b_annual_return, blv_annual_return))
    dates = [str(pp.start_date + timedelta(days=365)) for pp in past_portfolios] #already sorted by date
    stats = list(zip(dates, vols, returns, sharpes))
    return fig, stats

def live_calculate_past_portfolio_performance_hold(investment, portfolio):
    ''' Calculates the past performance of a portfolio live - without annual rebalancing, i.e. buy and hold. 
    May run into errors due to the inconsistency caused by a large number of stocks in the S&P 500 list in 2012 that have ceased trading prior to 2016.
    Annual rebalancing avoids this inconsistency as the data for historical S&P 500 constituents only needs to be available for the following year.

    :param investment: A positive integer.
    :param portfolio: A Portfolio object for which to calculate the past performance.

    :returns: A pair containing a html performance plot and zipped statistics.
    '''
    pp = Past_Portfolio.objects.filter(portfolio=portfolio).order_by('start_date').first() #must be ordered ascending
    start_date = pp.start_date #initial start date
    end_date = datetime.today().date() - timedelta(days=10)
    day_before_investing = start_date - timedelta(days=1)
    p_daily_values = [investment]
    b_daily_values = [investment]
    blv_daily_values = [investment]
    dates = [day_before_investing]
    stats, daily_values, daily_changes, ds = portfolioAnalyzer.simulate(start_date, end_date, pp.symbols, pp.allocations, p_daily_values[-1], b_daily_values[-1], blv_daily_values[-1])
    p_daily_values += list(daily_values[0])
    b_daily_values += list(daily_values[1])
    blv_daily_values += list(daily_values[2])
    dates += list(ds)
    p_annual_vols = [stats['volatility']]
    p_annual_return = [stats['return']]
    b_annual_vols = [stats['benchmark volatility']]
    b_annual_return = [stats['benchmark return']]
    blv_annual_vols = [stats['benchmarklv volatility']]
    blv_annual_return = [stats['benchmarklv return']]
    sharpes = [stats['sharpe']]
    fig = plot_graphs(p_daily_values, b_daily_values, blv_daily_values, dates)
    vols = list(zip(p_annual_vols, b_annual_vols, blv_annual_vols))
    returns = list(zip(p_annual_return, b_annual_return, blv_annual_return))
    dates = [str(start_date)]
    stats = list(zip(dates, vols, returns, sharpes))
    return fig, stats

def plot_graphs(p_vals, b_vals, blv_vals, dates):
    ''' Plots the portfolio's performance against the benchmarks (S&P 500 and S&P 500 Low Volatility Index).

    :param p_vals: A list containing the portfolio's daily values.
    :param b_vals: A list containing the S&P 500's daily values.
    :param blv_vals: A list containing the S&P 500 (LV)'s daily values.

    :returns: A html performance plot
    '''
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
    fig_html = mpld3.fig_to_html(fig)
    plt.close('all')
    return fig_html
    
def price(x):
    return '$%1.2f' % x

def update_or_create_portfolio(spread, period, lv, end, title="Custom", p=None):
    ''' Calculates the minimium volatility portfolio for the given parameters. Updates the existing portfolio object if it exists, otherwise creates a new one.

    :param spread: A positive integer <= 400.
    :param period: A positive integer <= 12.
    :param lv: A boolean value. True indcates to use only the 100 lowest volatility stocks.
    :param end: A date object indicating the date on which to calculate the portfolio.
    :param title(optional): A string - one of "Custom" or "Real".
    :param p(optional): The portfolio object to update.

    :returns: The updated/created portfolio object.
    '''
    start = end - timedelta(days=365*period)
    symbols = dba.get_symbols_performance(start, end, lv, current=True)
    allocations, symbols, vol = minimizer.calculate_portfolio(start, end, spread, symbols)
    if p is None:
        p = Portfolio(title=title, spread=spread, period=period, lv=lv)
    p.set_allocations(allocations)
    p.set_symbols(symbols)
    p.vol = vol
    return p

def update_past_portfolios(portfolio, end_date):
    ''' Calculates the past minimium volatility portfolios for a given portfolio.

    :param portfolio: A portfolio object for which to calculate the past portfolios.
    :param end_date: A date object indicating the date on which to calculate the portfolio.

    :returns: A list of updated past portfolios to be saved.
    '''
    bulklist = []
    annual_date = str(end_date.month) + str(end_date.day)
    pps = Past_Portfolio.objects.filter(portfolio=portfolio).order_by('start_date')
    if not pps.latest().start_date.year == (end_date.year - 1): #new year since last update
        new_pp = update_or_create_past_portfolio(portfolio, annual_date, end_date.year)
        new_pp.save()
    for pp in pps:
        bulklist.append(update_or_create_past_portfolio(portfolio, annual_date, pp.start_date.year, pp))
    return bulklist

def create_past_portfolios(portfolio, start_year, end_date):
    ''' Calculates the past minimium volatility portfolios for a given portfolio.

    :param portfolio: A portfolio object for which to calculate the past portfolios.
    :param start_year: A positive integer between 2001 and 2016 indicating the year on which to start.
    :param end_date: A date object indicating the date on which to calculate the portfolio.

    :returns: A list of new past portfolios to be saved.
    '''
    bulklist = []
    annual_date = str(end_date.month) + str(end_date.day)
    years = range(start_year, end_date.year)
    for year in years:
        bulklist.append(update_or_create_past_portfolio(portfolio, annual_date, year))
    return bulklist

def update_or_create_past_portfolio(portfolio, annual_date, year, pp=None):
    end = datetime.strptime(str(year)+ annual_date, '%Y%m%d').date() - timedelta(days=1)
    start = end - timedelta(days=365*portfolio.period)
    symbols = dba.get_symbols_performance(start, end, portfolio.lv, True)
    allocations, symbols, vol = minimizer.calculate_portfolio(start, end, portfolio.spread, symbols)
    if pp is None:
        pp = Past_Portfolio(portfolio=portfolio)
    pp.start_date=end #performance over the following year
    pp.set_allocations(allocations)
    pp.set_symbols(symbols)
    return pp

def pack_formated_data(shares, prices, symbols):
    nz = np.nonzero(shares)
    symbols = np.array(symbols)
    shares, prices, symbols = shares[nz], prices[nz], symbols[nz]
    shares = shares[np.argsort(symbols)]
    prices = prices[np.argsort(symbols)]
    investments = np.round(np.multiply(shares, prices), 2)
    invested = prices.dot(shares)
    company_data = dba.get_company_data(symbols)
    return list(zip(company_data, prices, shares, investments)), invested