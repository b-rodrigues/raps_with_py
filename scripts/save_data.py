import polars as pl
import polars.selectors as cs
import re

# The url below points to an Excel file
# hosted on the book's github repository
url = "https://is.gd/1vvBAc"

# Let's first download the file into a temporary file and then 
# return its path
from tempfile import NamedTemporaryFile
from requests import get

response = get(url)

with NamedTemporaryFile(delete = False, suffix = '.xlsx') as temp_file:
    temp_file.write(response.content)
    temp_file_path = temp_file.name
	
def read_excel(excel_file, sheet):
    out = pl.read_excel(
	    engine = 'xlsx2csv',
            source = excel_file,
            sheet_name = sheet,
            schema_overrides = {"Nombre d'offres": pl.String},
            read_options = {
            "skip_rows": 6,
            "has_header": True
            }
          ).with_columns(pl.lit(sheet).alias("year"))
    return out
	
def wrap_read_excel(sheet):
    out = read_excel(excel_file = temp_file_path,
                          sheet = sheet)
    return out
	
sheets = list(map(str, range(2010, 2022)))

raw_data = pl.concat(list(map(wrap_read_excel, sheets)))

def clean_names(string):
    # inspired by https://nadeauinnovations.com/post/2020/11/python-tricks-replace-all-non-alphanumeric-characters-in-a-string/
    clean_string = [s for s in string if s.isalnum() or s.isspace()]
    out = "".join(clean_string).lower()
    out = re.sub(r"\s+", "_", out)
    out = out.encode("ascii", "ignore").decode("utf-8")
    return out
	
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
      cs.all().str.strip_chars()
    )
    .with_columns(
      cs.contains("average").cast(pl.Float64, strict = False)
    )
    .with_columns(
      # In some sheets it's "Luxembourg", in others it's "Luxembourg-Ville"
      pl.col("locality").str.replace_all("Luxembourg.*", "Luxembourg")
    )
    .with_columns(
      # In some sheets it's "Pétange", in others it's "Petange"
      pl.col("locality").str.replace_all("P.*tange", "Pétange")
    )
)

raw_data = (
    raw_data
    .filter(~pl.col("locality").str.contains("Source"))
)

commune_level_data = (
    raw_data
    .filter(~pl.col("locality").str.contains("nationale|offres|Commune"))
    .filter(pl.col("locality").is_not_null())
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
    .select(cs.exclude("n_offers"))
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

from urllib.request import urlopen
from bs4 import BeautifulSoup
from pandas import read_html
from io import StringIO

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
    # This removes the dagger symbol next to certain communes names
    # in other words it turns "Commune †" into "Commune".
        pl.col("commune").str.replace_all(" .$", "")
    )
)

current_communes = list(current_communes_pl["commune"])

# Need to also check former communes
url = 'https://b-rodrigues.github.io/former_communes/#Former_communes/'

html = urlopen(url)

tables = (
    BeautifulSoup(html, 'html.parser')
    .find_all("table")
)

# The third table (...hence the '2' in tables[2]...) is the one we need
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

# There's certain communes with different spelling between
# wikipedia and our data, so let's correct the spelling
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
          .otherwise(pl.col("commune")).alias("commune")
    )
    .with_columns(
        pl.when(pl.col("commune").str.contains("City"))
          .then(pl.lit("Luxembourg"))
          .otherwise(pl.col("commune")).alias("commune")
    )
    .with_columns(
        pl.when(pl.col("commune").str.contains("K.*jeng"))
          .then(pl.lit("Kaerjeng"))
          .otherwise(pl.col("commune")).alias("commune")
    )
    .with_columns(
        pl.when(pl.col("commune").str.contains("P.*tange"))
          .then(pl.lit("Pétange"))
          .otherwise(pl.col("commune")).alias("commune")
    )
    .get_column("commune")
    .unique()
    .sort()
    .to_list()
)
