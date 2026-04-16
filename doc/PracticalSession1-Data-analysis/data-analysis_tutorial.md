To get some insights on the data used in this code environment, from **European Resource Adequacy Assessment (ERAA)**, you can plot very easily some quantities you would like to observe for different countries, years, climatic years. This is done running script [my_little_europe_data_analysis.py](../../my_little_europe_data_analysis.py), as explained below.

# How to run data analysis

**Update the JSON input file** dedicated to data analysis: [input/long_term_uc/data_analysis/data-analysis_params_to-be-modif.json](../../input/long_term_uc/data_analysis/data-analysis_params_to-be-modif.json). It contains a list of the quantities you would like to get plotted/saved in csv files; each element of this list being a dictionary with fields to specify the analysis/plot to be done:

  <!-- - **analysis_type** (<span style="color:#257cbd; font-weight:bold">str</span>): "plot" - to get some curves plotted e.g., demand of a given (country, year, climatic year); "plot_duration_curve" - idem for duration curve of a given quantity, typically (net) demand; "extract" to get some ERAA data extracted to a .csv file.  -->
  
  - **analysis_type** (<span style="color:#257cbd; font-weight:bold">str</span>):  - "plot" - to get some curves plotted e.g., demand of a given (country, year, climatic year)    
        <span style="margin-left: 123px;"> - "plot_duration_curve" - idem for duration curve of a given quantity, typically (net) demand  
        <span style="margin-left: 123px;"> - "extract" to get some ERAA data extracted to a .csv file
    
  - **data_type** (<span style="color:#257cbd; font-weight:bold">str</span>): datatype to analyze/plot; its value must be in the list of available values given in file [input/long_term_uc/functional_available-values.json](../../input/long_term_uc/functional_available-values.json) (e.g., "demand", "net_demand", "res_capa-factors", "fatal_production", "generation_capas", etc.). 
  
  - **country** (<span style="color:#257cbd; font-weight:bold">str</span> or <span style="color:#257cbd; font-weight:bold">list of str</span>): it must be in the list of values given in file [input/long_term_uc/elec-europe_eraa-available-values.json](../../input/long_term_uc/elec-europe_eraa-available-values.json) (field "countries").
      
      <span style="color:#257cbd; font-weight:bold">N.B.</span> If list of countries: if plots are displayed, multiple curves will be obtained (one for each country - on the same graph); if csv is written, data of the different countries will be concatenated.
  
  - **year** (<span style="color:#257cbd; font-weight:bold">int</span> or <span style="color:#257cbd; font-weight:bold">list of int</span>): year(s) to be considered for the data analysis; its value must be in the list of values given in file [input/long_term_uc/elec-europe_eraa-available-values.json](../../input/long_term_uc/elec-europe_eraa-available-values.json) (field “target_years”).  

      <span style="color:#257cbd; font-weight:bold"> N.B.</span> If list of years, same behaviour as for **country** field.
  
  - **climatic_year** (<span style="color:#257cbd; font-weight:bold">int</span> or <span style="color:#257cbd; font-weight:bold">list of int</span>): the (past) year from which weather conditions will be "extracted" and applied to current year; it must be in list given in file [input/long_term_uc/elec-europe_eraa-available-values.json](../../input/long_term_uc/elec-europe_eraa-available-values.json) (field "climatic_years")  

      <span style="color:#257cbd; font-weight:bold"> N.B.</span> If list of climatic years, same behaviour as for **country** field.
  
  - (optional) **aggreg_prod_types** (<span style="color:#257cbd; font-weight:bold">str</span>): aggreg. production types to analyze/plot; to be used only if datatype is "res_capa-factors", "net_demand" or "fatal_production", setting as value(s) the production types with capa factor data or "hydro_run_of_river" (the latter only if datatype=net_demand) to be extracted/saved, or used for net demand calculation.

    Attention: if data_type is "fatal_production", this parameter is mandatory (to indicate for which production units this quantity must be plotted)

    See [input/long_term_uc/elec-europe_eraa-available-values.json](../../input/long_term_uc/elec-europe_eraa-available-values.json) (field "aggreg_prod_types") to get list of per-country available production types, and select only the RES ones ("solar_pv", "wind_onshore", "wind_offshore", or "csp_nostorage") or "hydro_run_of_river".

    Default: all RES prod. types (respectively these ones and "hydro_run_of_river") if data_type=res_capa-factors (resp. data_type=net_demand) 

    N.B. If using this field with data_type="net_demand" a unique curve/data extract will be obtained; the name of output .png/.csv file will indicate which aggreg. prod. types have been used to get its content
  
  - **period_start** (<span style="color:#257cbd; font-weight:bold">str</span>, with date format <span style="color:#257cbd; font-weight:bold">yyyy/mm/dd</span>): start date of the period to be considered
    
  - **period_end** (<span style="color:#257cbd; font-weight:bold">str</span>, with date format <span style="color:#257cbd; font-weight:bold">yyyy/mm/dd</span>): end date of the period to be considered
  
  - **extra_params** (<span style="color:#257cbd; font-weight:bold">dict</span> or <span style="color:#257cbd; font-weight:bold">list of dict</span>): to specify extra-parameters that can be used to analyse data, e.g. fixed capacities for RES sources for net demand calculation.
    This dictionary has the following fields:
    
    - (optional) **label**: name of the case associated to this extra-params choice, that will be used for plot/csv saving
    
    - **values**: a dictionary with {param name: param value}. Only available param is currently **capas_aggreg_pt_with_cf**, for which 
    the following values can be used for ex. {"wind_onshore": 10000, "wind_offshore": 500, "solar_pv": 10000} to set capacity values of Wind on-/off-shore and Solar PV
    to 10GW, 500MW and 10GW respectively.

<span style="color:#257cbd; font-weight:bold">N.B.</span> If list are provided for countries, years, climatic years, and extra-params: if plots are displayed, a curve will be obtained for each case in the product of requested lists; if csv is written, concatenation will be done over the product of cases.
For plots a maximal number of 6 cases is allowed, so that obtained graph be readable.

An **example of such a JSON script is provided** in folder [input_example/long_term_uc/data_analysis](../../input_example/long_term_uc/data_analysis), 
providing some of the main cases that could be used for data analysis. In the same folder is given a file describing a few illustrative examples 
extracted from the JSON file

**Run script [my_little_europe_data_analysis.py](../../my_little_europe_data_analysis.py)**

**Outputs**

They will be obtained in folder [output/data_analysis](../../output/data_analysis): 
  - **either .png files**, if "plot" or "plot_duration_curve" chosen for "analysis_type" (cf. description above) or 
  - **.csv ones**, if "extract"
  - with explicit filenames - hopefully! -, of the form: 
  {data_type}_{country(ies)}_{year(s)}_cy{clim. year(s)}_{extra-params cases nber}.csv/png

N.B. For some obtained files, their name is not "totally explicit" with some suffix like "3-clim-years" if a selection 
of 3 climatic years has been requested. Re-running the same data analysis changing the values of these 3 climatic years - but keeping the same number of them - would overwrite this file. In turn...

**a good practice would be to save out of this environment the figures you would like to archive for your final analysis** (and synthesis to be written at the end of the week)
