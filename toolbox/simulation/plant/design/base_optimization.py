from hopp.type_dec import FromDictMixin
from attrs import define, field
from typing import List, Sequence, Optional, Union
from toolbox.simulation.ned_base import BaseClassNed
import pandas as pd
# from toolbox.simulation.ned_site import Site
import os
import numpy as np
from toolbox.simulation.plant.design.site_simplex import SiteSimplex
from hopp.simulation.technologies.wind.wind_plant import WindPlant
from hopp.simulation.technologies.pv.pv_plant import PVPlant
from hopp.simulation.technologies.battery import Battery
from hopp.simulation.technologies.grid import Grid
from hopp.simulation.hybrid_simulation import HybridSimulation
@define
class DesignVariable(FromDictMixin):
    re_plant: str
    flag: bool
    lower: float #in units of "unit"
    upper: float #in units of "unit"
    step: float  #in units of "unit"
    units: str
    # max_iter_for_simplex: int 
    simplex_keyname: str
    simplex_key_multiplier: float
    extra_simplex_sizes: List[float]  #in units of "unit"
    initial_simplex_sizes: Optional[List[float]]


@define
class OptimizeConfig(FromDictMixin):
    variables: List[DesignVariable]
    optimization_design_list: List[str]
    merit_figures: Union[List[str],str]
    simplex_design_case: dict
    optimization_params: dict
    use_existing_timeseries_info: bool
    existing_timeseries_data_info: dict = field(default = {})
    # def __attrs_post_init__(self):
    #     if not self.use_existing_timeseries_info:
    #         self.existing_timeseries_data_info = {}
        


@define 
class OptimalDesign(FromDictMixin):
    optimization_design_desc: str
    wind_size_mw: float = field(default = 0.0)
    pv_capacity_mwac: float = field(default = 0.0)
    include_battery: bool = field(default = False)


    

@define
class NelderMeadInputConfig(FromDictMixin):

    maxiter: Optional[int] = field(default = 20)
    xatol: Optional[Union[int,float]] = field(default = 6)
    fatol: Optional[Union[int,float]] = field(default = 0.1)
    adaptive: Optional[bool] = field(default = True)
    disp: Optional[bool] = field(default = False)

    options: dict = field(default = {})
    def __attrs_post_init__(self):
        self.options = {
            "maxiter":self.maxiter,
            "xatol":self.xatol,
            "fatol":self.fatol,
            "adaptive":self.adaptive}

@define
class SimulationResults(FromDictMixin):
    # optimization_desc: str
    atb_scenario: str
    re_plant_type: str
    h2_storage_type: str
    x_names: List[str]
    x_values_input: List[str]
    wind_size_mw_actual: float
    pv_size_mwdc_actual: float
    y_name: str
    y_value: float
    h2_storage_capacity: Optional[float]
    electrolyzer_cf: Optional[float]
    
    # def __attrs_post_init__(self):
    #     self.h2_storage_capacity = []
    
    def create_to_summary(self):
        d = self.as_dict()

        summary = {k:v for k,v in d.items()}
        y_name = summary.pop("y_name")
        y_val = summary.pop("y_value")
        summary.update({y_name:y_val})
        x_names = summary.pop("x_names")
        x_vals = summary.pop("x_values_input")
        for ii in range(len(x_names)):
            summary.update({x_names[ii]:x_vals[ii]})
        return summary


@define
class OptimizationResults(FromDictMixin):
    site: SiteSimplex
    Sim_Res: List[SimulationResults] = field(init = False)
    
    def __attrs_post_init__(self):
        self.Sim_Res = []
    
    def add_simulation_results(self,simulation_res:SimulationResults):
        self.Sim_Res.append(simulation_res)
    
    def make_Optimization_summary_results(self):
        temp = [pd.Series(self.Sim_Res[i].create_to_summary()) for i in range(len(self.Sim_Res))]
        return pd.DataFrame(temp)
    
    def save_Optimization_results(self,output_dir):
        # output_filepath_root = os.path.join(output_dir,"1b")
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}".format(self.site.id,self.site.latitude,self.site.longitude,self.site.state.replace(" ","")))
        opt_res = self.make_Optimization_summary_results()
        opt_res.to_pickle(output_filepath_root + "--Optimization_Tracker.pkl")


@define
class RenewableGenerationTracker(FromDictMixin):
    
    example_hopp_results: dict
    generation_profiles: dict
    ex_hybrid_plant: HybridSimulation = field(default = None)
    ex_wind_plant: WindPlant = field(default = None)
    ex_pv_plant: PVPlant = field(default = None)
    ex_battery: Optional[Battery] = field(default = None)
    ex_grid: Grid = field(default = None)

    def __attrs_post_init__(self):
         
        self.__setattr__("ex_hybrid_plant",self.example_hopp_results["hybrid_plant"])
        self.__setattr__("ex_wind_plant",self.example_hopp_results["hybrid_plant"].wind)
        self.__setattr__("ex_pv_plant",self.example_hopp_results["hybrid_plant"].pv)
        self.__setattr__("ex_grid",self.example_hopp_results["hybrid_plant"].grid)
        if self.ex_hybrid_plant.battery is not None:
            self.__setattr__("ex_battery",self.example_hopp_results["hybrid_plant"].battery)
        self.example_hopp_results.pop("hopp_interface")
        # self.example_hopp_results.pop("hybrid_npv")
        
    def add_generation_profile(self,hopp_results,wind_size_mw,pv_size_mwdc):
        
        if pv_size_mwdc>0:
            pv_profile_kwac = np.array(hopp_results["hybrid_plant"].pv.generation_profile)
            self.generation_profiles.update({"pv-{}".format(pv_size_mwdc):pv_profile_kwac})
        if wind_size_mw>0:
            wind_profile_kw = np.array(hopp_results["hybrid_plant"].wind.generation_profile)
            self.generation_profiles.update({"wind-{}".format(wind_size_mw):wind_profile_kw})

            



