# To start with: some general documentation

See [doc/useful_references.md](doc/useful_references.md) file to get 
- infos about ERAA (data) and PyPSA (framework/modeler)
- also some complementary sources of infos regarding the different countries you will be analysing

# Tutorial - Long-Term Unit Commitment (UC) part

## Running a N-countries (European) UC model by... only playing with 2 JSON files...

With the provided code environment you will be able to **run a Unit Commitment model by simply modifying the values in the 2 following files**:
1) [input/long_term_uc/elec-europe_params_to-be-modif.json](../../input/long_term_uc/elec-europe_params_to-be-modif.json) -> contain **some default values and global parameters** (e.g., temporal ones - with the UC period to be simulated). **See dedicated appendix below** for a detailed description of the different fields in this file
2) [input/long_term_uc/countries/](../../input/long_term_uc/countries/)*{**country**}.json* with "**country**" the name of your considered country -> the **values used in this file will overwrite values of preceding file**. This is to make your own country choice. **N.B.** In this file not only your own country parameters can be defined, but also the ones of the other countries - typically neighboring ones. This may seem surprising, but is related to the "solo" mode of this code environment described justafter. 

**(To be discussed later altogether) Importantly, note two distinguished behaviors of the code, whether "solo" or "Europe" mode be considered** - as defined in file [input/functional_params/usage_params.json](../../input/functional_params/usage_params.json), field "mode":
- if mode is set to **"solo", all country parameters (for your own country, but also for the rest of them) will be read from your own file *{country}.json***. 
Example: if in [germany.json](../../input/long_term_uc/countries/germany.json) dictionary associated to key "capacities_tb_overwritten" contains "france": {"nuclear": 0}, the French nuclear capacity will be set to 0MW for the UC simulated
- if mode is **"europe", parameters of each country will be extracted from file *{country}.json*; the rest of the values in this file being not accounted for**. 

**Open and run [my_little_europe_lt_uc.py](../../my_little_europe_lt_uc.py)**: you should get a log "THE END..." in the terminal window. If not, the "checkers" should have indicated you some aspects to be corrected in your - modified - parametrization (e.g., using some unavailable values for country or production types). 
    - (i) The only remaining bug that has been observed in this environment is when you have assets that can both produce and consume for the cumulated production plot (not possible in this case... will be corrected soon); however the .csv results data will have been saved. 
    - (ii) Note that run stops correctly - with an explicit error message in the logs - when optimisation problem solved by PyPSA does not have "optimal" status; in this case no output data (neither figures) are obtained.

## ... And directly getting output results for an extended analysis

**Obtained data (resp. plotted figures) results** are given in [output/long_term_uc/multizones_eur/data](../../output/long_term_uc/multizones_eur/data) (resp. [output/long_term_uc/multizones_eur/figures](../../output/long_term_uc/multizones_eur/figures)) folders.

In detail, and **except if the resolution of PyPSA optimization model was not successful**, it will give you: 
* (*data/* subfolder) **optimal production of all generators** considered in Europe, in a .csv file. **N.B.** The suffix of this file is indicating the year, climatic year ("cy") and the date of UC start period
* (*data/* subfolder) **"prices" for all countries** considered in Europe, in a .csv file. **N.B.** (i) Idem; (ii) Specifically, this prices are the optimal values of dual variables associated to suuply-demand equilibrium (for those who are familiar with optimization; otherwise it will be explained!) 
* (*figures/* subfolder) a **"cumulated vision" of the production**, in a .png file per country
* (*figures/* subfolder) **price curves**, for the different countries in a unique .png file

## Start preparing the "design" of your country/Europe system by playing with this UC tool

**Based on the numeric results obtained for each of the simulated configurations you can start "designing" (i.e. sizing the capacities) your own country** (if in "solo" mode)/European ("Europe" mode) system. Consider different:
* **seasons** -> by changing **uc_period_start** in file [input/long_term_uc/elec-europe_params_to-be-modif.json](../../input/long_term_uc/elec-europe_params_to-be-modif.json). **Question**: how would you select a few typical, or extreme, weeks to be considered to size your system? Is it possible to do it *ex-ante*, i.e. only looking at input data (e.g., demand, RES sources CF, installed generation capacities) or do you need some iterative process with UC runs to do that?
* **(target) years** -> using 2025 or 2033. **Question**: would your capacity design be similarly "efficient" at both horizons?
* **climatic years** -> how sensitive are your results to the choice of this parameter? in combination with the ones of the season (associated period)? **Question** how would you choose one/a few scenarios used for your investment planning decision-making?
* **interconnection capacities** -> how are your results sensitive to the limit on the flows that can be exchanged between your 7 countries? **N.B.** Playing with parameter **interco_capas_tb_overwritten** in file [input/long_term_uc/elec-europe_params_to-be-modif.json](../../input/long_term_uc/elec-europe_params_to-be-modif.json), you can get some preliminar insights on this
* (in solo mode) **What if... my neighbouring countries..." -> how are your individual country results sensitive to the decisions made by your neighbours? **N.B.** In solo mode you can exactly simulate the desired cases to try answering this question, by testing different configurations for your neighbours - in your own *{country}.json* file

# Appendices

## Input data description

**Preliminary remarks**: (i) JSON files used to store dict-like infos.  
<span style="margin-left: 140px;">(ii) Must start "directly" with "{" and end with "}".  
<span style="margin-left: 140px;">(iii) "null" is used for None in these JSON files.  
<span style="margin-left: 140px;">(iv) '.' (single quotes) not allowed in JSON files; use "." (double quotes) instead.  
<span style="margin-left: 140px;">(v) Tuples (.) not allowed; use rather lists [.].  

The ones in folder [input/long_term_uc](../../input/long_term_uc/); **file by file description** - starting with the two only ones to be modified:

- [elec-europe_params_to-be-modif.json](../../input/long_term_uc/elec-europe_params_to-be-modif.json):  
    - "<span style="color:#32B032; font-weight:bold">selected_climatic_year</span>": to **choose climatic year** considered for UC model (unique deterministic scenario, <span style="color:#257cbd; font-weight:bold">int</span> value)
    - "<span style="color:#32B032; font-weight:bold">selected_countries</span>": to **choose countries** that you would like to be part of your European- copper-plate - long-term UC model (<span style="color:#257cbd; font-weight:bold">list of string</span>; that must be in the set of considered countries for this class). **N.B.** Except if values are overwritten based on *{country}.json* files described hereafter, all production types available in ERAA data will be considered built for the countries in this list
    - "<span style="color:#32B032; font-weight:bold">selected_target_year</span>": to choose the ERAA (target) **year** to be simulated (<span style="color:#257cbd; font-weight:bold">int</span>, either 2025 or 2033)
    - "<span style="color:#32B032; font-weight:bold">selected_prod_types</span>": **per country selection of the (generation unit) aggregate production types** to be part of your model
    - "<span style="color:#32B032; font-weight:bold">uc_period_start</span>": **date from which UC optimization period starts; under format "1900/%M/%d"**. Ex.: "1900/1/1" to start from beginning of the year. **N.B.** "1900" to clearly indicate that a "fictive calendar" (modelling one) be used in ERAA data, with 364 days (to get 52 full weeks... an important granularity for some unit optim., as discussed in class)
    - (optional) "uc_period_end": idem, **end of period; same format**. Default value: period of 9 days starting from "uc_period_start".
    -  "<span style="color:#32B032; font-weight:bold">failure_power_capa</span>": **capacity of the failure - fictive - asset** considered (<span style="color:#257cbd; font-weight:bold">non-negative float</span>). **N.B.** Common to all countries
    -  "<span style="color:#32B032; font-weight:bold">failure_penalty</span>": **failure asset variable cost**, or more standardly "penalty" (<span style="color:#257cbd; font-weight:bold">non-negative float</span>). **N.B.** Typically set to a "very big" value, so that this asset be used as a last recourse - i.e. after having used all other production units at maximal power available
    -  "<span style="color:#32B032; font-weight:bold">interco_capas_tb_overwritten</span>": **values for the interconnection capacities**; to be used to overwrite - or complete - ERAA data (<span style="color:#257cbd; font-weight:bold">dictionary</span> with <span style="color:#257cbd; font-weight:bold">str</span> keys and <span style="color:#257cbd; font-weight:bold">non-negative float</span> values, with keys under format {origin country}2{destination country}). Ex:  {"france2poland": 10, "france2scandinavia": 0, "italy2iberian-peninsula": 0} will set interconnection capacity from France to Poland to 10GW (very fictive!) and from France to both Scandinavia et Iberian-Peninsula to 0GW. Note that regarding the France to Scandinavia link this value will be useless as there is no ERAA data associated to this link; in turn our code already used 0GW as the value. 

- [countries/](../../input/long_term_uc/countries/){**country**}.json*: 
    - "<span style="color:#32B032; font-weight:bold">team</span>": **name of your team**, i.e. name of the country you are "responsible for" (*str*, that must be in the set {"benelux", "germany", "iberian-peninsula", "poland", "scandinavia"} - use lower letters)
    - "<span style="color:#32B032; font-weight:bold">selected_prod_types</span>": list of **production types - using aggregate classes** defined in [input/long_term_uc/elec-europe_eraa-available-values.json](../../input/long_term_uc/elec-europe_eraa-available-values.json) file/field "aggreg_prod_types" (<span style="color:#257cbd; font-weight:bold">dictionary</span> {country name: list of aggreg. production types to be selected for run}). Ex: {"france": ["nuclear", "failure"], "germany": ["coal", "wind_onshore", "wind_offshore"]} will lead to a run with only nuclear and failure (resp. coal and wind on-/off-shore) units in France (resp. Germany) 
    - "<span style="color:#32B032; font-weight:bold">capacities_tb_overwritten</span>": **aggreg. production units for which you want to update the capacities - versus the ones in ERAA data**, and for the considered (target) year (<span style="color:#257cbd; font-weight:bold">dictionary</span> {country: aggreg. prod. type: updated capacity}). Ex: {"france": {"nuclear": 100000, "failure": 100000} will update French nuclear (aggreg.) capacity to 100GW and set a big failure asset of the same capacity. In this exemple, capacities for Germany will be taken as given in ERAA data. 

- (if too slow UC resolution time...) [solver_params.json](../../input/long_term_uc/solver_params.json):
    - "<span style="color:#32B032; font-weight:bold">name</span>": **name of the solver to be used** (*str*, that must be in the set {"highs", "gurobi"} - use lower letters)
    - (optional) "license_file": **name of the solver license file** (only for Gurobi; to be obtained from https://portal.gurobi.com/iam/register with your student email).
    **N.B.** This file has to be provided at the root of this project

- **[NOT TO BE MODIFIED during this practical class]** [elec-europe_eraa-available-values.json](../../input/long_term_uc/elec-europe_eraa-available-values.json): containing values available in the ERAA extract provided in folder [data/](../../data/): 
    - "<span style="color:#32B032; font-weight:bold">climatic_years</span>": **past historical years weather conditions** that are 'projected' on ERAA "target year" (<span style="color:#257cbd; font-weight:bold">list of int</span> values)
    - "<span style="color:#32B032; font-weight:bold">countries</span>": your seven **(meta-)countries**, the only ones for which ERAA data are made available in this code environment (<span style="color:#257cbd; font-weight:bold">list of str</span>)
    - "<span style="color:#32B032; font-weight:bold">aggreg_prod_types</span>": **per country and year aggregated production types** (<span style="color:#257cbd; font-weight:bold">two-level dictionary</span> in format {country name: {(target) year: list of aggregated production types available in the extract of ERAA data}}). **N.B.** As "aggregated production types" are only used here to simplify the considered model (diminishing its size), availability of such a type means that at least one of the corresponding - more detailed - ERAA production types is available in data
    - "<span style="color:#32B032; font-weight:bold">target_years</span>": list of **years available** here - 2025 or 2033 here, identically to the toy example (<span style="color:#257cbd; font-weight:bold">list of int</span>)
    - "<span style="color:#32B032; font-weight:bold">intercos</span>": list of **interconnection with available data** (<span style="color:#257cbd; font-weight:bold">list of str</span>, with str under format {origin country}2{destination country}). **N.B.** Obtained by simple aggregation of ERAA data when multiple sub-zones are present in our (meta-)countries

**ATTENTION** (for next class): actually marginal cost values for Eur. UC model are extracted from following file... put it in the list of the ones to be modified by students?

- **[NOT TO BE MODIFIED]** [elec-europe_params_fixed.json](../../input/long_term_uc/elec-europe_params_fixed.json): 
    - "<span style="color:#32B032; font-weight:bold">aggreg_prod_types_def</span>": **correspondence between "aggregate" production type (the ones that will be used in this class) and the ones - more detailed - in ERAA data**. It will be used in the data reading phase; to simplify (diminish size!) of the used data in this UC exercise
    - "<span style="color:#32B032; font-weight:bold">available_climatic_years</span>", "available countries", "available_target_years" (or simply years; "target year" is the used terminology in ERAA): **available values for the dimensions of provided extract of ERAA data**
    - "<span style="color:#32B032; font-weight:bold">gps_coordinates</span>": the ones of the capitals excepting meta-countries with coordinates of Rotterdam for "benelux", Madrid for "iberian-peninsula", and Stockholm for "scandinavia". **N.B.** Only for plotting - very schematic - representation of the "network" associated to your UC model
    - "<span style="color:#32B032; font-weight:bold">eraa_edition</span>": edition of ERAA data used - 2023.2 (one/two ERAA editions per year from 2021)

- **[NOT TO BE MODIFIED]** [functional_available-values.json](../../input/long_term_uc/functional_available-values.json):  
    - "<span style="color:#32B032; font-weight:bold">datatypes</span>": list of **type of data names**. Used only for the data crunch session; based on script [my_little_europe_data_analysis.py](../my_little_europe_data_analysis.py) - see associated doc
  
- **[NOT TO BE MODIFIED]** [pypsa_static_params.json](../../input/long_term_uc/pypsa_static_params.json):  
    - "<span style="color:#32B032; font-weight:bold">min_unit_params_per_agg_pt</span>": list of minimal parameters to be provided when creating different types of generators in PyPSA
    - "<span style="color:#32B032; font-weight:bold">generator_params_default_vals</span>": default values applied when creating PyPSA generators
