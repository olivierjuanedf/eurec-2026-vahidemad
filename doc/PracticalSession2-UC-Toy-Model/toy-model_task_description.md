# Objectives of the practical session n°2: 
1. Model a simple 1-country Unit Commitment Problem using PyPsa
2. Have an introduction to PyPsa optimisation framework


# Stages of the practical session:

## First step - with the Italian Case
1. Run [my_toy_ex_italy.py](../my_toy_ex_italy.py)
2. Look at the results obtained with this script, written in output/long_term_uc. Describe and comment on these results.
3. Read [my_toy_ex_italy.py](../my_toy_ex_italy.py) and associated [toy_model_params/italy_parameters.py](../toy_model_params/italy_parameters.py), following comments in them to understand the main stages when writing a PyPSA model

## Second step - with your own country
4. **Read and follow the steps written in [doc/PracticalSession2-UC-Toy-Model/toy-model_tutorial.md](../PracticalSession2-UC-Toy-Model/toy-model_tutorial.md)** to create the UC model for your own country
5. **Run your script** to optimise your single-country Unit Commitment model
6. **Observe/analyse** the obtained solution in folders *output/long_term_uc/monozone_{country}/data* and *.../figures*
**Do you get a "feasible" solution?** An intuitive shape for the production profile of the different assets?

