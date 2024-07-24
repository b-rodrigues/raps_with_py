import polars as pl
import polars.selectors as cs
from plotnine import ggplot, geom_line, aes, ggsave

commune_level_data = pl.read_csv("commune_level_data.csv")
country_level_data = pl.read_csv("country_level_data.csv")

commune_level_data = (
    commune_level_data
    .with_columns(
        pl.when(pl.col("year") == 2010)
          .then(pl.col("average_price_nominal_euros")).over("locality").alias("p0"),
        pl.when(pl.col("year") == 2010)
          .then(pl.col("average_price_m2_nominal_euros")).over("locality").alias("p0_m2")
    )
    .with_columns(
        cs.starts_with("p0").forward_fill().over("locality")
    )
    .with_columns(
        pl = pl.col("average_price_nominal_euros")/pl.col("p0")*100,
        pl_m2 = pl.col("average_price_m2_nominal_euros")/pl.col("p0_m2")*100
    )
)

filtered_data = (
  commune_level_data.filter(pl.col("locality") == "Luxembourg")
)

lux_plot = (
    ggplot(filtered_data) +
    geom_line(aes(y = "pl_m2",
                  x = "year",
                  group = "locality",
                  colour = "locality"))
)

filtered_data = (
  commune_level_data.filter(pl.col("locality") == "Esch-sur-Alzette")
)

esch_plot = (
    ggplot(filtered_data) +
    geom_line(aes(y = "pl_m2",
                  x = "year",
                  group = "locality",
                  colour = "locality"))
)

mamer_plot = (
    ggplot(commune_level_data.filter(pl.col("locality") == "Mamer")) +
    geom_line(aes(y = "pl_m2",
                  x = "year",
                  group = "locality",
                  colour = "locality"))
)

schengen_plot = (
    ggplot(commune_level_data.filter(pl.col("locality") == "Schengen")) +
    geom_line(aes(y = "pl_m2",
                  x = "year",
                  group = "locality",
                  colour = "locality"))
)

wincrange_plot = (
    ggplot(commune_level_data.filter(pl.col("locality") == "Wincrange")) +
    geom_line(aes(y = "pl_m2",
                  x = "year",
                  group = "locality",
                  colour = "locality"))
)

# Let's save the plots
lux_plot.save(filename = "lux_plot.pdf", path = "plots/")
esch_plot.save(filename = "esch_plot.pdf", path = "plots/")
mamer_plot.save(filename = "mamer_plot.pdf", path = "plots/")
schengen_plot.save(filename = "schengen_plot.pdf", path = "plots/")
wincrange_plot.save(filename = "wincrange_plot.pdf", path = "plots/")

# Alternative way with join
#p0_pl = (
#commune_level_data
#    .filter(
#        pl.col("year") == 2010
#    )
#    .with_columns(
#        p0 = pl.col("average_price_nominal_euros"),
#        p0_m2 = pl.col("average_price_m2_nominal_euros")
#    )
#    .select(
#        ["locality", "year", "p0", "p0_m2"]
#    )
#)
#
#commune_level_data = (
#commune_level_data
#    .join(p0_pl,
#          how = "left",
#          on = ["locality", "year"],
#          )
#    .with_columns(
#        cs.starts_with("p0").forward_fill().over("locality")
#    )
#)

