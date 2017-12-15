import wikipedia
from bs4 import BeautifulSoup

'''This module provides a an API for retrieving the latest S&P 500 constituents from Wikipedia.'''

def get_current_consituents():
	''' Retreives current S&P 500 constituents their data from Wikipedia.

	:returns: Nested list of S&P 500 constituents and their data.
	'''
	html = wikipedia.WikipediaPage("List of S&P 500 companies").html()
	soup = BeautifulSoup(html, "html.parser")
	table = soup.findChild("table")
	#headings = [th.get_text() for th in table.find("tr").find_all("th")]
	datasets = [[td.get_text().strip() for td in row.find_all("td")] for row in table.find_all("tr")[1:]]
	return datasets
