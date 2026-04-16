TODO - basculer/vider ce fichier sur les issues du projet Github ?
Q : sont-ils bien conservés si ensuite un nouveau projet est créé ? (idem opération début du cours d'Olivier J.) 

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
MAIN actions (M)
M0) (IMPORTANT!) Unique prod types def. in (i) all data files, (ii) constants of the codes (@dataclass) 
and (iii) input JSON files 
-> suppressing redundant constants/input data?
-> pb with wind_onshore vs wind_on_shore for ex...
-> (OB, 4/4/2026) Fait dans le code ; resterait à vérif/unifier dans les données... (pour l'instant reformatage fait 
à la lecture)
M1) Switch to PyPSA 1.0?
M2) Update readme.md -> screenshots with new names for project 
M3) Remove unnecessary/redundant constants 
-> align as much as possible on PyPSA language in input data?
M4) Check marginal cost/efficiency values in elec-europe_params_fixed.json
M5) See "TODO[debug]"
M6) [CR] Voir "TODO[CR]"
M7) Prévoir appui (doc/mini-script ?) pour aider les étudiants à gérer les infaisabilités ? (bcp au début... surtout si on leur fait passer les embûches pédagos - ne pas mettre d'actif défaillance par ex !)
M8) Tester avec des dates start/end sans hh:mm
-> déjà géré ? (normalement)
M9) Sortir/tracer les émissions CO2
M11) Vérif cohérence FuelNames avec ProdTypeNames -> utilité des 2 ?
-> supprimer redondance pour éviter confusions...
M12) Virer les gitignore qui traînent...
M13) Trier/simplifier JSON visibles des élèves -> pour que cela soit facile pour eux de rentrer dedans (ne leur laisser voir que les params utilisateurs). Et adapter doc en fonction
M14) Introduce aggreg. META prod types -> "all_res". To avoid typing lists of all RES types for selection...
M15) Reformat data files description with file objects (folder, separators, column names...)
M16) Select only data of considered cys when reading data in dataset.py\get_countries_data (and other filtering...)
-> seems not TB done for all dts
M17) Test Jules from Google to rapidly reformat/add tests to this code project?
-> https://jules.google/
M18) Réel intérêt du mode solo vs. europe ou seulement confusant pour les élèves ?

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
DATA (D)
D0) 1900 fictive calendar supposing to start a Monday (the case in reality; check of in ERAA data)?
-> to be specified in data\ERAA_2023-2\data_description.txt
D0bis) Unit of hydro data? Scale accordingly when reading
-> to be specified in same file
D1) Add ERAA ed. 2024, with climatic modelling...
D2) Pb with hydro data/week idx when both day and week given they seem equal...
D3) Fix solar thermal key issue - identical to the one with solar_pv vs lfsolarpv previously?
D4) Redondances country.json et europe_tb_modif.json ?

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
DATA ANALYSIS (DA) - before 1st UC run, to get an intuition of the pbs - my_little_europe_data_analysis.py
DA1) Add datatype=production in possible values (for agg. prod types for which production is known as an input parameter)
DA3) (improve code quality) Avoid creating Dataset object once per data analysis - getting once all data needed (however it should be done
on the product of data needs -> more than needed in general)
DA4) Allow capacity plot/extract - over multiple years and dts?
DA6) Replace [-2] by an adaptive index to refer to extra-params idx at some stages
DA7) Allow case (extract, load duration curve) - currently only possible to plot it
DA8) Integrate hydro\RoR data in net_demand calc case -> already ok? (maybe not big impact...)
DA9) Improve names of CF/fatal prod figures when only 1 agg pt selected (xx_agg-pt-name_yyy_1-agg-pt -> last part of suffix useless)
DA10) (Bogue) Cas avec solar_pv/wind_offshore et 2 années clim... Pb to get a product on 2 dims ? (CY and agg pt)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
TOY EX (T) - my_toy_ex_italy.py. Some tasks shared with Eur (E) case following
T1) Fullfill long_term_uc/toy_model_params/italy_parameters.py with complem exs in Ita case (hydro, batteries, dsr)
T2) Do NOT mention diff of PV key between capa and CF data -> confusing for the students...
T3) Keep FUEL_SOURCES or too complex for the students?
-> may be redundant with input/long_term_uc/elec-europe_params_fixed.json -> CONFUSING!
T/E4) Add min/max soc and generation constraints for the stock/hydro
-> needs to do it via Linopy (even for 1.0 version)
In Store object e_min_pu/e_max_pu but some other key params seem to be missing... (recommended in v1.0
doc to use Storage for hydro...)
-> cf. include\dataset_builder.py add_hydro_extreme_levels_constraint and add_hydro_extreme_gen_constraint functions init
T/E5) Add dyn constraints, and associated params in input (JSON) files/ex in Ita case (in toy_model_params\italy_parameters.py)
T6) Introduce possibility to parametrize init_soc in input/long_term_uc/elec-europe_params_to-be-modif.json
-> in some extra-params section to be introduced?
T7) Add possibility to have a CO2 limit on unique / multiple zone(s) -> with GlobalConstraint in PyPSA
T/E8) ror with p_set input of PyPSA -> not integrated currently?
E9) Add possibility to overwrite hydro capas (power and energy) - apparently not accounted for currently 
(cf. eelisa students comments)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
EUROPE SIMUS (E) (my_little_europe_lt_uc.py)
E1) Usage param auto fulfill interco capa missing -> ??
E2) Add possibility to set Stock (additional to ERAA data) in JSON tb modif input file
E3) Add possibility to provide additional fatal demand -> for iterations between UC and imperfect disaggreg of an aggregate DSR flex (EV for ex) modeled as a Stock for ex! (cf. OMCEP course)
E4) Reformat/simplify JSON params file (in input/long_term_uc/elec-europe_params_to-be-modif.json
-> suppress "selec" prefix implicit for some params?
E5) Get dual variable associated to link capa constraint
-> not directly provided in PyPSA... needs to get it from Linopy
-> cf. include\dataset_builder.py, get_link_capa_dual_var_opt function init
E6) Connecter qques nouveaux params au JSON Eur 
-> SOC_init pour les (gros) stocks?
-> Use "from_json_tb_modif" keyword in input\long_term_uc elec-europe_params_fixed.json
(currently only "from_eraa_data" used)
-> ctes dynamiques aussi
E7) Add link congestion calculation -> % of link capa usage
-> stat metrif of this in UCSummary

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
RUNNER (R) (main_runner.py)
R1) Finish v1 runner
-> (OJ) Copier le dossier .devcontainer (idem projet ElectricSystemPlanning) dans ce projet aussi -> pourquoi ?
-> automatically over multiple projects cloned?
R2) Script to generate some graphs/ppt(s) after launching the runner
-> for archive/discussing live with the students
R3) "Stress tests": blackout on some countries * pts; issue on some intercos; techno. breakthrough on some pts
R4) Save summary of input/output params in a JSON
R5) Calculate metrics vs ERAA case (wo any modifs in JSON inputs)
-> capas diff? Associated cost? Etc.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
PLOTS
P1) Eco2mix colors TB completed -> coal; and markets to distinguish agg_prod_type with same colors
P2) Introduce subfolders in output\figures directory to sort them (prod, link, etc.)
P3) Check case with unique curve -> plot_dims obtained from UC ts name (call of def get_dims_from_uc_ts_name)
P4) Plot tot export per country (on a unique graph)
-> cf include\dataset_builder.py\init plot_cum_export_flows_at_opt func
P5) Fix pb with plots -> some curves missing (RES) due to plot_params sep ('-' io '_'?)
-> put also an option to add stock contribution (dispatch and store) in this stacked figure
(include\dataset_builder.py\def plot_opt_prod_var)
-> may be related to M0
P6) Set default color in \input\functional_params\plot_params.json if 1 curve only (a group observed that it was - randomly? - 
set to yellow in this case... not very visible!) 
P7) Ajouter graphe camembert à la Damien JACOMY ("sunburst")
-> to show congestion of intercos in an "aggreg. view"
-> 'sunburst' graph, with different levels - (i) links (the more congested); (ii) season (summer/winter); 
(iii) period in week (open day, 4h-block), (week-end day, 4h-block) could do 12 areas
-> cf. code ex. provided by Damien JACOMY (EDF)
P8) Save output graphs in html to allow interactive discussions
P9) Plot capa sizing vs ERAA "initial" data
P10) Plot (histogram?) of distribution of link congestion level per link and season
-> 1 fig per (origin) country
-> with one block of cumulated bars (summer + winter) showing the distribution per link with neighbouring countries
P11) Congestion level duration curve with 1 figure per country and 1 curve per link with neighb. countries

OTHERS
O1) Doc basic use of codespace out of the repot?
O2) Version Python dispos sous le codespace 3.9-3.12 -> mettre dans la doc/cmd pour l'obtenir 
O3) / by efficiency in FuelSources and not * for primary cost?
O4) Iberian-peninsula -> Iberia ?
O5) Check multiple links between two zones possible. Cf. ger-scandinavia AC+DC in CentraleSupélec students hypothesis.
And interco types (hvdc/hvac) ok? Q2Emmanuel NEAU and Jean-Yves BOURMAUD
O6) Scripts avec qques exemples de base Python ? "[coding tricks]"
O7) Subpart of git with distinguished access-rights between students / TA for docs and data available?
(to avoid conflicts; changes leading to "un-necessary" bugs)
O8) Finish and connect type checker for JSON file values -> using map(func, [val]) and all([true])
-> OK excepting UsageParameters
O9) Add Excel plugin to have a nice view of csv in codespace -> rainbow csv?
O10) Plot params check to be coded -> cf. check() with only bob=1 in plot_params.py