# Objectives of the practical session n°3: 
1. Discover the code environment that will be the base of the serious game
2. Play with the European Serious Game

# Stages of the practical session:

## Discovering the code environment
1. Read [doc/PracticalSession3-European-System-Planning/European-system_tutorial.md](../PracticalSession3-European-System-Planning/European-system_tutorial.md)

2. Check parameters in [input/long_term_uc/countries/](../../input/long_term_uc/countries/)*{**country**}.json* with "**country**" the name of your considered country 

3. Check parameters in [input/long_term_uc/elec-europe_params_to-be-modif.json](../../input/long_term_uc/elec-europe_params_to-be-modif.json).

4.  Check parameters in [input/functional_params/usage_params.json](../../input/functional_params/usage_params.json) : for the moment you should be in “solo” mode. Put your country name in the field “team”.

5. Run [my_little_europe_lt_uc.py](../../my_little_europe_lt_uc.py) 
    - First to check that it works correctly.
    - What is the result of the optimization? Why?

6. Using yesterday’s data analysis of your country, update file  [input/long_term_uc/countries/](../../input/long_term_uc/countries/)*{**country**}.json*  to add production capacities to your country. Try different electricity mixes until you obtain a feasible UC problem.

7. Once your UC problem is feasible, check the results : data in csv files are available in [output/long_term_uc/multizones_eur/data](../../output/long_term_uc/multizones_eur/data) and plotted figures in [output/long_term_uc/multizones_eur/figures](../../output/long_term_uc/multizones_eur/figures). What can you say about the prices ?

## Playing with the European Serious Game
8. Now you can start playing with the parameters in file [input/long_term_uc/elec-europe_params_to-be-modif.json](../../input/long_term_uc/elec-europe_params_to-be-modif.json)
    - Change the season -> by changing **uc_period_start**
    - Change the target year
    - Change the climatic year
    - Change interconnection capacities

→ Observe the impact on the optimal solution and on the prices when running [my_little_europe_lt_uc.py](../../my_little_europe_lt_uc.py).
→ How would you construct an electricity mix resilient to these different scenarios?
