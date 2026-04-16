Description of the **input data examples**: 
- **For data analysis** script [my_little_europe_data_analysis.py](../../../my_little_europe_data_analysis.py)
- **Extracting cases** (dictionaries of parameters) **from** [input_example/long_term_uc/data_analysis/data-analysis_params_to-be-modif.json](../../../input_example/long_term_uc/data_analysis/data-analysis_params_to-be-modif.json)

# Start simple

- **Plot unique case** -> obtain graph with a unique curve in file *demand_france_2025_cy1985.png* (in 
folder [output/data_analysis](../../../output/data_analysis))

```json
    {
  "analysis_type": "plot",
  "data_type": "demand",
  "countries": "france",
  "years": 2025,
  "climatic_years": 1985
}
```

- **Extract data** for the same unique case -> obtain *demand_france_2025_cy1985_1-1to14.csv*, the final
  suffix - specifying the temporal period considered — by default, the first two weeks of the year

```json
    {
  "analysis_type": "extract",
  "data_type": "demand",
  "countries": "france",
  "years": 2025,
  "climatic_years": 1985
}
```

- **Change the type of data** (to get RES capa. factors), **country and climatic year** -> *res_capa-factors_italy_2025_cy1989_3-aggpts.png*. 
N.B. In this case all (3) production types with capa. factor data are obtained; and the filename is not "totally explicit"

```json
    {
  "analysis_type": "plot",
  "data_type": "res_capa-factors",
  "countries": "italy",
  "years": 2025,
  "climatic_years": 1989
}
```

- **Get another type of data** (net demand) and specify another temporal period (last two weeks of January)...

```json
        {
  "analysis_type": "plot",
  "data_type": "net_demand",
  "countries": "france",
  "years": 2025,
  "climatic_years": 1985,
  "period_start": "1900/1/15",
  "period_end": "1900/1/29"
}
```

- Now **plot duration curve** for two countries...

```json
        {
  "analysis_type": "plot_duration_curve",
  "data_type": "demand",
  "countries": [
    "france",
    "germany"
  ],
  "years": 2025,
  "climatic_years": 1985
}
```

- Select **only part of the (aggreg.) production types** for RES capa. factors plot/csv extract, here "solar_pv" and "
  wind_offshore".
  N.B. This is done here for a combination of 2 years and 2 climatic years; in total 8 curves will be obtained.

```json
     {
  "analysis_type": "plot",
  "data_type": "res_capa-factors",
  "aggreg_prod_types": [
    "solar_pv",
    "wind_offshore"
  ],
  "countries": "france",
  "years": [
    2025,
    2033
  ],
  "climatic_years": [
    1985,
    1987
  ],
  "period_start": "1900/1/15",
  "period_end": "1900/1/29"
}
```

# More advanced

- Usage of **extra_params** field to change generation capacity values **for data_type=net_demand** calculation ->
  obtain *net_demand_france_2025_cy1985_2-extraparams.png*. 
  N.B. In this case two extra-params cases have been introduced - in addition
  to the reference one, with capacity data from ERAA, with labels "res_low" and "res_high"

```json
        {
  "analysis_type": "plot",
  "data_type": "net_demand",
  "countries": "france",
  "years": 2025,
  "climatic_years": 1985,
  "period_start": "1900/1/15",
  "period_end": "1900/1/29",
  "extra_params": [
    null,
    {
      "label": "res_low",
      "values": {
        "capas_aggreg_pt_with_cf": {
          "wind_onshore": 10000,
          "wind_offshore": 500,
          "solar_pv": 10000
        }
      }
    },
    {
      "label": "res_high",
      "values": {
        "capas_aggreg_pt_with_cf": {
          "wind_onshore": 40000,
          "wind_offshore": 10000,
          "solar_pv": 40000
        }
      }
    }
  ]
}
```

- Select **only part of the (aggreg.) production types** for net demand calculation (and then plot/csv extract).
  N.B. Attention in this case only two curves will be plotted; the selection of prod. types is only accounted for in
  net demand calculation, here: net_demand = demand - cf(solar_pv) - cf(wind_onshore)

```json
    {
  "analysis_type": "plot_duration_curve",
  "data_type": "net_demand",
  "aggreg_prod_types": [
    "solar_pv",
    "wind_onshore"
  ],
  "countries": "france",
  "years": 2025,
  "climatic_years": [
    1985,
    1987
  ],
  "period_start": "1900/1/15",
  "period_end": "1900/1/29"
}
```
