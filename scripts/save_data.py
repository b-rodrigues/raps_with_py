import polars as pl
import polars.selectors as cs
import re

# Polars can read all the sheets of an Excel workbook
# in one go and return a list of sheets, but I want to
# add a column with the year. So I write this function
# that reads the sheet and adds the column. I then
# map this function over a list of sheet names.
def read_excel(excel_file, sheet):
    out = pl.read_excel(
            source = excel_file,
            sheet_name = sheet,
            read_csv_options = {
            "skip_rows": 6,
            "has_header": True
            }
          ).with_columns(pl.lit(sheet).alias("year"))
    return out

# This function sets the excel_file argument so that I
# map over ’sheet’
def wrap_read_excel(sheet):
    out = read_excel(excel_file = "vente-maison-2010-2021.xlsx",
                          sheet = sheet)
    return out

# This creates a list of sheet names to map over
sheets = list(map(str, range(2010, 2022)))

# I can now map the function over the list of sheets
# and concatenate them into a single polars data frame
# using pl.concat.
raw_data = pl.concat(list(map(wrap_read_excel, sheets)))

# This function will be used below to clean the column names
# If I was using Pandas, I could have used clean_columns from skimpy
# but unfortunately this function doesn’t work with Polars DFs.
# So I write this little function to clean the column names instead.
def clean_names(string):
    # inspired by https://nadeauinnovations.com/post/2020/11/python-tricks-replace-all-non-alphanumeric-characters-in-a-string/
    clean_string = [s for s in string if s.isalnum() or s.isspace()]
    out = "".join(clean_string).lower()
    out = re.sub(r"\s+", "_", out)
    out = out.encode("ascii", "ignore").decode("utf-8")
    return out

# This row-binds all the datasets (first converting the dict to a list), and
# then renames the columns using the above defined function
# Not as nice as skimpy.clean_columns, but works on Polars DataFrames
raw_data = raw_data.select(pl.all().name.map(clean_names))

raw_data = (
    raw_data
    .rename(
      {
        "commune": "locality",
        "nombre_doffres": "n_offers",
        "prix_moyen_annonc_en_courant": "average_price_nominal_euros",
        "prix_moyen_annonc_au_m_en_courant": "average_price_m2_nominal_euros"
      }
    )
    .with_columns(
        cs.contains("average").cast(pl.Float64, strict = False)
    )
    .with_columns(
        # In some sheets it’s "Luxembourg", in others it’s "Luxembourg-Ville"
      pl.col("locality").str.replace_all("Luxembourg.*", "Luxembourg")
    )
    .with_columns(
        # In some sheets it’s "Pétange", in others it’s "Petange"
      pl.col("locality").str.replace_all("P.*tange", "Pétange")
    )
    .with_columns(
      pl.col("locality").str.strip_chars()
    )
)

# Always look at your data
(
raw_data
.filter(pl.col("average_price_nominal_euros").is_null())
)


# Remove empty locality
raw_data = (
    raw_data
    .filter(~pl.col("locality").is_null())
)

# Only keep communes in the data

commune_level_data = (
    raw_data
    .filter(~pl.col("locality").str.contains("nationale|offre|Source"))
    # This is needed on Windows...
    .with_columns(
        pl.col("locality").str.replace_all("\351", "é")
    )
    .with_columns(
        pl.col("locality").str.replace_all("\373", "û")
    )
    .with_columns(
        pl.col("locality").str.replace_all("\344", "ä")
    )
)

country_level = (
    raw_data
    .filter(pl.col("locality").str.contains("nationale"))
    .select(~cs.contains("n_offers"))
)

offers_country = (
    raw_data
    .filter(pl.col("locality").str.contains("Total d.offres"))
    .select(["year", "n_offers"])
)

country_level_data = (
    country_level.join(offers_country, on = "year")
    .with_columns(pl.lit("Grand-Duchy of Luxembourg").alias("locality"))
)

# I can use all these comments

# if the data already had a year column, I could have read all the sheets
# in one go using the following code

#datasets = pl.read_excel(
#    source = "vente-maison-2010-2021.xlsx",
#    sheet_id = 0,
#    read_csv_options = {
#        # Polars skip empty rows that that come before any data by default, which is quite helpful
#        # with Pandas, 10 rows should get skipped for sheets 2010 to 2020, but only 8 for sheet 2021
#        # but in the case of Polars, because empty rows get skipped automatically, 6 more rows
#        # must get skipped. Check out the Excel file to see what I mean.
#        "skip_rows": 6,
#        "has_header": True#,
#        # new_columns would be the preferred approach, but for some reason when using it on this Excel File,
#        # two more empty columns appear. So I could call them a and b and then remove them
#        # this is what the commented line below does. However, I decided to apply a function
#        # that cleans the column names myself. It’s more complicated, but also more elegant as it would
#        # work for any number of columns and in any order
#        # "new_columns": ["a", "b","locality", "n_offers", "average_price_nominal_euros", "average_price_m2_nominal_euros"]
#    }
#)


# We now need to scrape wikipedia for a table

from urllib.request import urlopen
from bs4 import BeautifulSoup
from pandas import read_html
from io import StringIO
# also need to install lxml

# we now need to scrape wikipedia pages
url = 'https://b-rodrigues.github.io/list_communes/'

html = urlopen(url)

tables = (
    BeautifulSoup(html, 'html.parser')
    .find_all("table")
)

current_communes_raw = read_html(StringIO(str(tables[1])))[0]

# current_communes has a MultiIndex, so drop it
current_communes_raw.columns = current_communes_raw.columns.droplevel()

current_communes_pl = (
    pl.DataFrame(current_communes_raw)
    .select(pl.col("Name.1").alias("commune"))
    .with_columns(
        pl.col("commune").str.replace_all("\351", "é")
    )
    .with_columns(
        pl.col("commune").str.replace_all("\373", "û")
    )
    .with_columns(
        pl.col("commune").str.replace_all("\344", "ä")
    )
    .with_columns(
        pl.col("commune").str.replace_all(" .$", "")
    )
)

current_communes = list(current_communes_pl["commune"])

# Test whether all the communes are in our data
# If the next expression returns an empty list
# then we’re good

(
commune_level_data
 .filter(~pl.col("locality").is_in(current_communes))
 .get_column("locality")
 .unique()
 .sort()
 .to_list()
)

# Need to also check former communes
url = 'https://b-rodrigues.github.io/former_communes/#Former_communes/'

html = urlopen(url)

tables = (
    BeautifulSoup(html, 'html.parser')
    .find_all("table")
)

# The third table (...hence the ’2’ in tables[2]...) is the one we need
former_communes_raw = read_html(StringIO(str(tables[2])))[0]

former_communes_pl = (
    pl.DataFrame(former_communes_raw)
    .with_columns(
        pl.col("Name").str.replace_all("\351", "é")
    )
    .with_columns(
        pl.col("Name").str.replace_all("\373", "û")
    )
    .with_columns(
        pl.col("Name").str.replace_all("\344", "ä")
    )
    .select(pl.col("Name").alias("commune"))
)

# Combine former and current communes

communes = (
    pl.concat([former_communes_pl, current_communes_pl])
    .get_column("commune")
    .unique()
    .sort()
    .to_list()
)


(
commune_level_data
 .filter(~pl.col("locality").is_in(communes))
 .get_column("locality")
 .unique()
 .sort()
 .to_list()
)

# There’s certain communes with diffirent spelling between
# wikipedia and our data, so let’s correct the spelling
# on the wikipedia ones
# ['Clémency', 'Erpeldange', 'Kaerjeng', 'Luxembourg', 'Pétange']

communes_clean = (
    pl.concat([former_communes_pl, current_communes_pl])
    .with_columns(
        pl.when(pl.col("commune").str.contains("Cl.mency"))
          .then(pl.lit("Clémency"))
          .otherwise(pl.col("commune")).alias("commune")
    )
    .with_columns(
        pl.when(pl.col("commune").str.contains("Erpeldange"))
          .then(pl.lit("Erpeldange"))
          .otherwise(pl.col("commune")).alias("commune"),

    )
    .with_columns(
        pl.when(pl.col("commune").str.contains("City"))
          .then(pl.lit("Luxembourg"))
          .otherwise(pl.col("commune")).alias("commune"),
    )
    .with_columns(
        pl.when(pl.col("commune").str.contains("K.*jeng"))
          .then(pl.lit("Kaerjeng"))
          .otherwise(pl.col("commune")).alias("commune"),
    )
    .with_columns(
        pl.when(pl.col("commune").str.contains("P.*tange"))
          .then(pl.lit("Pétange"))
          .otherwise(pl.col("commune")).alias("commune"),
    )
    .get_column("commune")
    .unique()
    .sort()
    .to_list()
)

# Test whether all the communes are in our data
# If the next expression returns an empty list
# then we’re good

(
commune_level_data
 .filter(~pl.col("locality").is_in(communes_clean))
 .get_column("locality")
 .unique()
 .sort()
 .to_list()
)

# save data as csv

commune_level_data.write_csv("commune_level_data.csv")
country_level_data.write_csv("country_level_data.csv")
