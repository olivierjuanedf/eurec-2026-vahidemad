# Objectives of the practical session n°1: 
1. Provide a **short “electrical portrait”** of your country doing some data crunch
2. **“Manually” solve the capacity planning problem** for your own country (as if non-interconnected in Europe) using the so-called **“Screening curve methodology"**

# Stages of the practical session:

1. **Read [doc/PracticalSession1-Data-analysis/data-analysis_tutorial.md](../PracticalSession1-Data-analysis/data-analysis_tutorial.md)**

2. **Run [my_little_europe_data_analysis.py](../../my_little_europe_data_analysis.py)** 
  - First to check that it is functional!
  - Then, to get the infos that you seem necessary to start to “draw the elec. portrait” of your country. Some key infos to start with may be: the level of demand and residual demand, and the availability of renewables.

3. **Get data and plot the (residual) load duration curve of your country**, for some selected year in the future, using [my_little_europe_data_analysis.py](../../my_little_europe_data_analysis.py). 
N.B. If you want you can use some other info of your country “elec. portrait” that may be useful for this task (among the ones available in data-analysis tool, or with complementary calculations/plots done on your side - outside of the code env.)

4. Based on manual calculations, or on external Excel/simple Python script (out of code env.), **calculate the capacity** of the different production types **you would like to invest in your system**

5. **Create some slides to present the "electricity portrait" of your country** to the other students. Some key information could include: the level of demand, the availability of renewables, the capacities you have chosen to invest in, and the associated price of electricity.

6. *(Optional) What are the limits of the screening curve approach? Could it explain the - potential?! - differences that you obtain in your capacities vs. the ones given in ERAA data (available in data/ in code env.)?*