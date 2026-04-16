from dataclasses import dataclass


@dataclass
class AnalysisTypes:
    calc: str = 'calc'
    # only extract data from data folder and put it in output folder
    extract: str = 'extract'
    # idem, put putting it on 'matricial format', with different climatic years in column
    extract_to_mat: str = 'extract_to_mat'
    plot: str = 'plot'  # simple plot
    plot_duration_curve: str = 'plot_duration_curve'  # duration curve plot
    plot_rolling_horizon_avg: str = 'plot_rolling_horizon_avg'  # rolling horizon avg plot


ANALYSIS_TYPES = AnalysisTypes()
ANALYSIS_TYPES_PLOT = [ANALYSIS_TYPES.plot, ANALYSIS_TYPES.plot_duration_curve, ANALYSIS_TYPES.plot_rolling_horizon_avg]
AVAILABLE_ANALYSIS_TYPES = list(ANALYSIS_TYPES.__dict__.values())
COMMON_PLOT_YEAR = 1900
