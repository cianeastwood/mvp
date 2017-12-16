# Minimium Volatility Portfolios
A fast, flexible and self-maintaining real-time web application which calculates minimum volatility portfolios (MVPs). Historical portfolio volatility is optimally minimised to calculate the MVP. 

## Prerequisites
* Stock database (available on request)
* Python 3.4.2+, NumPy, SciPy, Django, ...
  * pip install -r requirements.txt

## Starting the web application
* python manage.py runserver

## Functionality
* Instantly calculate a custom and optimal MVP using live stock prices on the New York Stock Exchange (NYSE).
  * **Input:** desired investment, range of historical minimisation period (in years), low volatility stocks only (boolean)
  * **Output:** MVP, it's consituent stocks and corresponding shares, performance statistics over minimisation period
* Secure admin site
  * Self-maintaining stock database using Yahoo Finance


## Data model
* **Company:** Stores a single company entry.
* **Stock:** Stores a single stock entry. Each stock is related to a single company. 
* **SNP500:** Stores a single year and the corresponding S&P 500 constituents on the 1st of January of that year. Each object is related to many companies.
* **Portfolio:** Stores a single minimum-volatility portfolio for specific parameters. Allocations are real-valued and sum to one, hence are independent of investment. Only symbols with non-zero allocations are stored. This significantly boosts performance when retrieving stocks for those symbols.
* **Plot**: Stores a single past performance plot. Each object stores the plot that results from scaling the related portfolio allocations by a specific investment, rounding to the closest share and plotting its past performance against suitable benchmarks. Hence, each object is related to a single portfolio.
* **Past_Portfolio:** Stores a single past portfolio, i.e., a past minimum-volatility portfolio for the minimisation parameters of it’s related portfolio. Enables precalculation of the minimisation function at specific dates in the past. Like portfolio, it is independent of investment to allow flexibility.
* **Past_Statistics:** Stores a single past statistics record for a given past portfolio and investment (plot object). Each object stores performance statistics over the year following the start date of the related past portfolio. Like the plot object, the allocations of the related past portfolio are scaled by the investment of the related plot and rounded to the closest share before calculating performance statistics over the following year. As a result, the past_statistics and plot objects are updated simultaneously. 
