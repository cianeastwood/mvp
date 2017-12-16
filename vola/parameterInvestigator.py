from vola import minimizer, portfolioAnalyzer
from db import access as dba
from datetime import datetime, timedelta
import matplotlib.pyplot as plt, mpld3
import matplotlib.dates as mdates
import numpy as np

'''
This module is for investigating parameter correlations through graph analysis.

It enables the investigation of the effect of each parameter on volatility, return and risk-adjusted return.
'''

annual_date = '0101'

def test_parameter(variables, fixed_variables, lvs, var_name, fixed_var_name, start, end):
    for fixed in fixed_variables:
        print(fixed)
        for lv in lvs:
            print(lv)
            avg_vol, std_vol, std_ret, avg_ret, avg_rar, std_rar = [], [], [], [], [], [] 
            for variable in variables:
                print(variable)
                if var_name == "Spread":
                    vol, s_vol, s_ret, ret, risk_ajd_return, s_rar = parameter_testing(start, end, variable, fixed, lv)
                else:
                    vol, s_vol, s_ret, ret, risk_ajd_return, s_rar = parameter_testing(start, end, fixed, variable, lv)
                avg_vol.append(vol)
                avg_ret.append(ret)
                avg_rar.append(risk_ajd_return)
                std_vol.append(s_vol)
                std_ret.append(s_ret)
                std_rar.append(s_rar)
            title = "{0} Investigation '06: LV={1}, {2}={3}".format(var_name, lv, fixed_var_name,fixed)
            v_plt = plot_graphs_parameters(avg_vol, variables, "AVG VOL", var_name, title)
            v_plt.savefig('vola/research/parameters/{0}/Vol_{1}_{2}_06'.format(var_name, fixed, lv))
            r_plt = plot_graphs_parameters(avg_ret, variables, "AVG RETURN", var_name, title)
            r_plt.savefig('vola/research/parameters/{0}/Return_{1}_{2}_06'.format(var_name, fixed, lv))
            vs_plt = plot_graphs_parameters(std_vol, variables, "STD VOL", var_name, title)
            vs_plt.savefig('vola/research/parameters/{0}/Vol_std_{1}_{2}_06'.format(var_name, fixed, lv))
            rs_plt = plot_graphs_parameters(std_ret, variables, "STD RETURN", var_name, title)
            rs_plt.savefig('vola/research/parameters/{0}/Return_std_{1}_{2}_06'.format(var_name, fixed, lv))
            rar_plt = plot_graphs_parameters(avg_rar, variables, "AVG RISK-ADJ RETURN", var_name, title)
            rar_plt.savefig('vola/research/parameters/{0}/Risk_adj_return_{1}_{2}_06'.format(var_name, fixed, lv))
            rar_std_plt = plot_graphs_parameters(std_rar, variables, "STD RISK-ADJ RETURN", var_name, title)
            rar_std_plt.savefig('vola/research/parameters/{0}/Risk_adj_return_std_{1}_{2}_06'.format(var_name, fixed, lv))
            plt.close('all')

def parameter_testing(start, end, minimum_spread, period, lv): 
    vols, rets, risk_adj_rets = [],[],[]
    for year in range(start, end):
        end = datetime.strptime(str(year) + annual_date, '%Y%m%d').date()
        start = end - timedelta(days=365*period)
        symbols = get_symbols(start, end, lv)
        allocations, symbols, min_vol = minimizer.calculate_portfolio(start, end, minimum_spread, symbols)
        vol, ret, risk_adj_ret = portfolioAnalyzer.calc_stats_params(end, end + timedelta(days=365), symbols, allocations)
        vols.append(vol)
        rets.append(ret)
        risk_adj_rets.append(risk_adj_ret)
    return np.mean(vols), np.std(vols), np.std(rets), np.mean(rets), np.mean(risk_adj_rets), np.std(risk_adj_rets)

def plot_graphs_parameters(values, params, value_name, param_name, title):
    fig, ax = plt.subplots()
    ax.plot(params, values, linewidth=1)
    plt.xlabel(param_name)
    plt.ylabel(value_name)
    plt.title(title)
    return plt

def get_symbols(start, end, lv):
    symbols = dba.get_valid_symbols_check(start, end)
    avail_next_year = dba.get_valid_symbols(end, end + timedelta(days=365))
    symbols = list(set(symbols).intersection(avail_next_year))
    if lv:
    	symbols = dba.get_lowest_100_vol(symbols, end)
    return symbols

if __name__ == '__main__':
	''' Saves plots of the minimisation parameters against both the averages and standard deviations of the performance volatility, return and risk-adjusted return.'''
	#avoid survivorship bias - as many available symbols as possible (drops massively in '01)
	#max minimisation period for accurate testing is 5 here (min year - max period = 1 => 2006 - 5 = 1)
	train_start = 2000
	train_end = 2006
	spreads = [25, 50, 75, 100] #[1, 25, 50, 100]
	periods = [1,2,4,8] #, 5, 8, 10]
	lvs = [False]
	#test_parameter(periods, spreads, lvs, "Period", "Spread", train_start, train_end)
	test_parameter(spreads, periods, lvs, "Spread", "Period", train_start, train_end)
