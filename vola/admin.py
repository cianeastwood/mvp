from django.contrib import admin, messages
from .models import Company, SNP500, Portfolio, Plot
import db.maintenance_multiprocessing as db
from datetime import datetime, timedelta

'''This module configures the admin application and provides a web API for database updates.'''

def update_recent_SNP500_stock_data(ModelAdmin, request, queryset):
	total_data, companies = db.update_recent_admin(list(queryset))
	if total_data is None:
		messages.success(request, "Recent SNP500 stock data is already up to date.")
	else:
		messages.success(request, "Updated recent SNP500 stock data. Inserted {0} daily prices for {1} companies. See log file for more details.".format(total_data, companies))

def update_all_stock_data(ModelAdmin, request, queryset):
	total_data, companies = db.update_stocks(list(queryset))
	if total_data is None:
		messages.success(request, "All stock data is already up to date.")
	else:
		messages.success(request, "Updated all stock data. Inserted {0} daily prices for {1} companies. See log file for more details.".format(total_data, companies))

def update_current_SNP500_constituents(ModelAdmin, request, queryset):
	snp = queryset[0]
	if not (len(queryset) == 1 and snp.year==0):
		messages.error(request, "Only the current SNP500 constituents can be updated.")
		return None
	added, removed, new_company_data = db.update_current_SNP500(snp)
	if not added:
		messages.success(request, "Current SNP500 constituents already up to date.")
	else:
		messages.success(request, "Updated current SNP500 constituents:\nAdded:{0}\nRemoved:{1}".format(added, removed))
		if new_company_data is False:
			messages.warning(request, "Stock data was unavailable for some new companies. See log file for more details.")

def select_suggested_portfolio(ModelAdmin, request, queryset):
	if len(queryset) != 1:
		messages.error(request, "Must select exactly one portfolio to set as suggested.")
	else:
		updated = db.select_suggested_portfolio(queryset.first())
		if updated:
			messages.success(request, "Set suggested portfolio.")
		else:
			messages.success(request, "Selected portfolio is already the suggested portfolio.")

def update_portfolios(ModelAdmin, request, queryset):
	update_period_days = 7
	if queryset.first().date_calculated >= datetime.today().date() - timedelta(days=update_period_days):
		messages.success(request, "Portfolios already updated in the past {0} days.".format(update_period_days))
	else:
		db.update_portfolio_calculations(queryset)
		messages.success(request, "Updated Portfolios.")

def update_plots_and_statistics(ModelAdmin, request, queryset):
	update_period_days = 7
	if queryset.first().date_calculated >= datetime.today().date() - timedelta(days=update_period_days):
		messages.success(request, "Plots and Statistics already updated in the past {0} days.".format(update_period_days))
	else:
		db.update_portfolio_performances(queryset)
		messages.success(request, "Updated Plots and Statistics.")

class CompanyAdmin(admin.ModelAdmin):
	list_display = ['symbol', 'name']
	ordering = ['symbol']
	actions = [update_recent_SNP500_stock_data, update_all_stock_data]

class SNP500Admin(admin.ModelAdmin):
	list_display = ['readable']
	ordering = ['year']
	actions = [update_current_SNP500_constituents]

class PortfolioAdmin(admin.ModelAdmin):
	list_display = ['title', 'lv', 'period', 'spread', 'date_calculated']
	ordering = ['title', 'lv', 'period', 'spread']
	actions = [update_portfolios, select_suggested_portfolio]

class PlotAdmin(admin.ModelAdmin):
	list_display = ['investment', 'portfolio', 'date_calculated']
	ordering = ['investment', 'date_calculated']
	actions = [update_plots_and_statistics]

admin.site.register(SNP500, SNP500Admin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Portfolio, PortfolioAdmin)
admin.site.register(Plot, PlotAdmin)
admin.site.disable_action('delete_selected')