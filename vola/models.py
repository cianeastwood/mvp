from django.db import models
from django.utils import timezone
import json
import numpy as np

'''
This module provides Django models containing essential fields and behaviors of the data. 

->Each model maps to a single database table.
->Each attribute of the model represents a database field.
->Allows Django to automatically generate a database-access API.
'''

class Company(models.Model):
    """
    Stores a single company entry.
    """
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.symbol
    
    symbol = models.CharField(max_length=10, primary_key=True) #[0]
    name = models.CharField(max_length=100) #[1]
    sector = models.CharField(max_length=100) #[3]
    sub_industry = models.CharField(max_length=100) #[4]
    hq_address = models.CharField('Address of Headquarters', max_length=100) #[5]

    def get_most_recent_price(self):
        try:
            stock_obj = Stock.objects.filter(company__symbol=self.symbol).latest()
        except Stock.DoesNotExist:
            return None
        return stock_obj.close_price
    

class Stock(models.Model):
    """
    Stores a single stock entry, related to :model:`vola.Company`.
    """
    class Meta:
        verbose_name = "Stock"
        unique_together = (('company', 'date'),)
        get_latest_by = "date"

    def __str__(self):
        return self.company.symbol + ": " + str(self.date)

    company = models.ForeignKey(Company)
    #reduce max digits?
    close_price = models.DecimalField(max_digits=12, decimal_places=2) # €
    change = models.DecimalField(max_digits=20, decimal_places=12) # %
    date = models.DateField() 

class SNP500(models.Model):
    """
    Stores a single SNP500 year, related to :model:`vola.Company`.
    """
    class Meta:
        verbose_name = "SNP500"
        get_latest_by = "year"

    def __str__(self):
        return str(self.year)

    def readable(self):
        if self.year==0:
            return "SNP500 Constituents - Current"
        else:
            return "SNP500 Constituents on 01-01-{0}".format(self.year)

    year = models.IntegerField(primary_key=True)
    companies = models.ManyToManyField(Company)

class Portfolio(models.Model):
    """
    Stores a single portfolio for specific parameters.
    """
    class Meta:
        verbose_name = "Portfolio"
        unique_together = (('title', 'spread', 'period', 'lv'),)

    def __str__(self):
        return "{0}:{1},{2},{3}".format(self.title, self.lv, self.period, self.spread)

    title = models.CharField(max_length=30)
    spread = models.IntegerField('Minimum Spread')
    period = models.IntegerField('Minimisation Period')
    lv = models.BooleanField('Low Volatility Stocks Only')
    vol = models.DecimalField('Minimised Volatility', max_digits=6, decimal_places=4)
    allocations_field = models.TextField(editable=False)
    symbols_field = models.TextField(editable=False)
    date_calculated = models.DateField(auto_now=True)
    suggested = models.BooleanField(default=False)

    def __init__(self, *args, **kw):
        self.allocations = np.array([])
        self.symbols = []
        super(Portfolio, self).__init__(*args, **kw)
        if self.allocations_field:
            self.allocations = np.array(json.loads(self.allocations_field))
        if self.symbols_field:
            self.symbols = json.loads(self.symbols_field)

    def save(self, *args, **kw):
        self.set_allocations(self.allocations)
        self.set_symbols(self.symbols)
        super(Portfolio, self).save(*args, **kw)

    def set_allocations(self, allocations):
        self.allocations_field = json.dumps(list(allocations))

    def set_symbols(self, symbols):
        self.symbols_field = json.dumps(symbols)

#large field + rarely available/accessed -> store seperately for optimisation
class Plot(models.Model):
    """
    Stores a single plot, related to :model:`vola.Portfolio`.
    """
    class Meta:
        unique_together = (('portfolio', 'investment'),)

    def __str__(self):
        return self.portfolio.__str__()

    portfolio = models.ForeignKey(Portfolio)
    investment = models.IntegerField(default=0)
    html = models.TextField(null=True)
    date_calculated = models.DateField(auto_now=True)

class Past_Portfolio(models.Model):
    """
    Stores a single past portfolio, related to :model:`vola.Portfolio`.
    """
    class Meta:
        unique_together = (('portfolio', 'start_date'),)
        get_latest_by = "start_date"

    def __str__(self):
        return "{0}:{1},{2},{3},{4}".format(self.portfolio.title, self.portfolio.lv, self.portfolio.period, self.portfolio.spread, self.start_date)

    portfolio = models.ForeignKey(Portfolio)
    start_date = models.DateField() #performance over the following year
    allocations_field = models.TextField(editable=False) #volatility minimised over the previous 'period' num years
    symbols_field = models.TextField(editable=False)
    
    def __init__(self, *args, **kw):
        self.allocations = np.array([])
        self.symbols = []
        super(Past_Portfolio, self).__init__(*args, **kw)
        if self.allocations_field:
            self.allocations = np.array(json.loads(self.allocations_field))
        if self.symbols_field:
            self.symbols = json.loads(self.symbols_field)
 
    def save(self, *args, **kw):
        self.set_allocations(self.allocations)
        self.set_symbols(self.symbols)
        super(Past_Portfolio, self).save(*args, **kw)

    def set_allocations(self, allocations):
        self.allocations_field = json.dumps(list(allocations))

    def set_symbols(self, symbols):
        self.symbols_field = json.dumps(symbols)

class Past_Statistics(models.Model):
    """
    Stores a single past statistics record, related to :model:`vola.Past_Portfolio` and
    :model:`vola.Plot`.
    """
    def __str__(self):
        return self.past_portfolio.__str__()

    past_portfolio = models.ForeignKey(Past_Portfolio)
    plot = models.ForeignKey(Plot)
    #performance statistics over the following year
    vol = models.DecimalField('Volatility', max_digits=6, decimal_places=4)
    ret = models.DecimalField('Return', max_digits=6, decimal_places=4)
    snp_vol = models.DecimalField('SNP500 Volatility', max_digits=6, decimal_places=4)
    snp_ret = models.DecimalField('SNP500 Return', max_digits=6, decimal_places=4)
    snp_lv_vol = models.DecimalField('SNP500LV Volatility', max_digits=6, decimal_places=4)
    snp_lv_ret = models.DecimalField('SNP500LV Return', max_digits=6, decimal_places=4)
    sharpe_ratio = models.DecimalField(max_digits=6, decimal_places=4)