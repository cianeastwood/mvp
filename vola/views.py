from django.shortcuts import render
from django.http import HttpResponse
from vola.portfolioCalculator import calculate_portfolio
from db.access import get_investments, get_periods, get_spreads, get_suggested_portfolio_performance

'''This module provides functions that respond to web requests.'''

def index(request):
	context = {} 
	return render(request, 'vola/index.html', context)

def performance(request):
	fig, stats = get_suggested_portfolio_performance()
	context = {'fig': fig, 'stats':stats}
	return render(request, 'vola/performance.html', context)

def custom(request):
	investment, minimum_spread, period, lv, performance, live = get_parameters(request)
	if not valid_parameters(investment, minimum_spread, period):
		investments = get_investments()
		periods = get_periods()
		context = {'investments': investments, 'periods': periods}
		return render(request, 'vola/custom.html', context)
	lv = True if lv == "true" else False
	performance = True if performance == "true" else False
	live = True if live == "true" else False
	share_data, invested, min_vol, fig, stats = calculate_portfolio(int(investment), int(minimum_spread), lv, performance, live, int(period))
	context = {'investment': investment, 'minimum_spread': minimum_spread, 'period': period, 'lv': lv, 'performance':performance,
			   'share_data': share_data, 'invested': invested, 'min_vol': min_vol, 'fig': fig, 'stats':stats}
	return render(request, 'vola/custom_performance.html', context)

def about(request):
	context = {}
	return render(request, 'vola/about.html', context)

def get_parameters(request):
	investment = request.GET.get('investment', '')
	minimum_spread = request.GET.get('minimum_spread', '')
	period = request.GET.get('period', '')
	lv = request.GET.get('lv', '')
	performance = request.GET.get('performance', '')
	live = request.GET.get('live', '')
	return investment, minimum_spread, period, lv, performance, live

def valid_parameters(investment, min_spread, period):
	min_invest = 1500
	max_invest = 100000000
	inv_check = investment.isdigit() and int(investment) >= min_invest and int(investment) <=max_invest
	spread_check = min_spread.isdigit() and int(min_spread) in get_spreads()
	period_check = period.isdigit() and int(period) in get_periods()
	return inv_check and spread_check and period_check