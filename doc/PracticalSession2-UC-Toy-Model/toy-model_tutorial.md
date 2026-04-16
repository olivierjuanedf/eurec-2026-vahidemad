# Start simple, with a "toy model" (of a unique country Unit Commitment model)

This **session exercise consists in**:
* **Adapting both scripts** [my_toy_ex_italy.py](../../my_toy_ex_italy.py) and associated [toy_model_params/italy_parameters.py](../../toy_model_params/italy_parameters.py)
* **Modeling a simple 1-country (the one you are responsible for) *Unit Commitment* (UC) problem in PyPSA**.  
    <span style="color:#257cbd; font-weight:bold">N.B.</span> Monday's theoretical session by Cécile ROTTNER has explained this UC - optimisation - problem in details... summarized in one sentence, it could be: "How can electricity demand be satisfied at the lowest possible cost by optimising the production decisions of the available generation assets?"

You can **proceed in order** to model your own country:
1. **Copy/paste the two scripts described above and rename them** *my_toy_ex_{**country**}.py* and *toy_model_params/{**country**}_parameters.py* - with "***country***" the name of your country (or create two new ones with same names)

2. **Considering installed generation assets data from file** *data/ERAA_2023-2/generation_capas/generation-capa_{**year**}_{**country**}.csv* - with "***year***" the one considered in this simulation, update values list of generator (dictionaries) in list of function *get_generators* in script *{**country**}_parameters.py*. This mainly consists in:  
    - (i) Extracting from Italy case the assets that are also present in your country, and only adapt "**p_nom**" value based on *generation-capa_{**year**}_{**country**}.csv* file;  
    - (ii) Complement the obtained list with assets in *generation-capa_{**year**}_{**country**}.csv* for the ones not present in Italy. Ex: looking at file [toy_model_params/ex_italy-complem_parameters.py](../../toy_model_params/ex_italy-complem_parameters.py) - again setting "**p_nom**" based on values in generation capas csv file.

Note also that **available values in data** (years, climatic years, aggregate production types, etc.) **can be found in file** [input/long_term_uc/elec-europe_eraa-available-values.json](../../input/long_term_uc/elec-europe_eraa-available-values.json)

3. **Run your script** to optimise your single-country Unit Commitment model

4. **Observe/analyse** the obtained solution in folders *output/long_term_uc/monozone_{country}/data* and *.../figures*
**Do you get a "feasible" solution?** An intuitive shape for the production profile of the different assets?


# More information: to understand/modify PyPSA code

Based on the **two following websites**:

* PyPSA documentation: https://pypsa.readthedocs.io/en/latest/
* ERAA documentation (2023.2 will be used): https://www.entsoe.eu/outlooks/eraa/

and an **"extract" of PyPSA documentation regarding generator objects given below**, you could be able to build your own country "Unit Commitment" model/modify provided piece of code.

**Main parameters to define PyPSA generator objects** - that could be sufficient in this course:
* (required) **bus** -> to which the generator is attached. 
    * **Format**: <span style="color:#257cbd; font-weight:bold">str</span>
* (required) **name** -> of your generation asset (used as id). In the proposed piece of code format {technology type}_{country name} is used (ex: "coal_poland"). 
    * **Format**: <span style="color:#257cbd; font-weight:bold">str</span>
* (optional) **carrier** -> mainly primary energy carriers. Can be also used to model CO2eq. emissions. 
    * **Format**: <span style="color:#257cbd; font-weight:bold">str</span>
* (optional) **committable** -> with "dynamics constraints" accounted for?
    * **Format**: <span style="color:#257cbd; font-weight:bold">boolean</span>
    * **Default**: <span style="color:#ff2c1c; font-weight:bold">False</span>
* (optional) **efficiency** -> of your generator - as a % (related to losses in "generation process"). 
    * **Format**: <span style="color:#257cbd; font-weight:bold">float</span>
    * **Default**: <span style="color:#ff2c1c; font-weight:bold">1</span>
* (optional) **marginal_cost**. 
    * **Format**: <span style="color:#257cbd; font-weight:bold">float</span>
* (optional) **"p_nom"** -> capacity (a power, in MW). 
    * **Format**: <span style="color:#257cbd; font-weight:bold">int</span> 
    * **Default**: <span style="color:#ff2c1c; font-weight:bold">0</span>
* (optional) **p_min_pu** -> minimal power level - as % of capacity ("pu" stands for "per unit"), set to 0 to start simple.                 
    * **Format**: <span style="color:#257cbd; font-weight:bold">float</span> or <span style="color:#257cbd; font-weight:bold">vector</span> (list or NumPy array).  
    * **Default**: <span style="color:#ff2c1c; font-weight:bold">0</span>
* (optional) **p_max_pu** → idem, maximal power. Can integrate "Capacity Factors" (or maintenance); in this case it can be variable in time.  
  * **Format**: <span style="color:#257cbd; font-weight:bold">float</span> or <span style="color:#257cbd; font-weight:bold">vector</span> (list or NumPy array).  
  * **Default**: <span style="color:#ff2c1c; font-weight:bold">1</span>
