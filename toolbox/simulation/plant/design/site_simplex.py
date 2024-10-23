from hopp.simulation.base import BaseClass
from toolbox.simulation.ned_base import BaseClassNed
from typing import Iterable, List, Sequence, Optional, Union, TYPE_CHECKING

import numpy as np
from hopp.type_dec import hopp_float_type
from hopp.utilities.validators import contains, range_val, gt_zero
from attrs import define, field
import copy
import os
import pandas as pd


@define
class SiteSimplex(BaseClassNed):
    latitude: hopp_float_type = field(converter = hopp_float_type)
    longitude: hopp_float_type = field(converter = hopp_float_type)
    
    distance_to_salt_cavern: float = field(converter = hopp_float_type)
    distance_to_rock_cavern: float = field(converter = hopp_float_type)

    balancing_area: Optional[str] = field(default = None)

    state: Optional[str] = field(default=None)
    county: Optional[str] = field(default=None)
    CountyFP: Optional[float] = field(default=None)
    id: Optional[float] = field(default=None)

    rock_cavern_loc: Optional[str] = field(default=None)
    salt_cavern_loc: Optional[str] = field(default=None)
    feedstock_region: str = field(default="US Average", validator=contains(['East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central','US Average']))
    
    initial_simplex_data: Optional[pd.DataFrame] = field(default = None) 
    initial_simplex: Optional[pd.DataFrame] = field(default = None) 
    
    full_simplex: Optional[pd.DataFrame] = field(default = None) 
    optimization_tracker: Optional[pd.DataFrame] = field(default = None)
    optimization_simplex: Optional[pd.DataFrame] = field(default = None)

    # pd.DataFrame() = field(default = None)
    design_variables_info: dict() = field(default = None) #optimization_config["design_variables"]
    # simplex_case_info: dict() = field(default = None) #optimization_config["driver"]["design_of_simplex"]
    merit_figures: List[str] = field(default=[])
    # merit_figure: str = field(default="lcoh") #optimization_config["merit_figure"]
    design_variables: Optional[List[str]] = field(default = None)
    # design_variables_bounds: tuple = field(default = None)
    design_variables_mapper: Optional[dict] = field(default={})
    # full_simplex: pd.DataFrame() = field(default = None)

    def __attrs_post_init__(self):
        self.optimization_tracker = pd.DataFrame()
        self.optimization_simplex = pd.DataFrame()
        design_variables = self.design_variables_info.keys()
        design_variables = [k for k in self.design_variables_info.keys() if self.design_variables_info[k]["flag"]]
        self.design_variables = design_variables
        self.design_variables_mapper = {}
        for var in self.design_variables:
            self.design_variables_mapper.update({self.design_variables_info[var]["re_plant"]:var})
        # self.design_variables_bounds = self.design_variables_info

    def get_bounds_for_plant_design(self,re_plant_type):
        if "wind" in re_plant_type:
            
            wind_lb = self.design_variables_info[self.design_variables_mapper["wind"]]["lower"]
            wind_ub = self.design_variables_info[self.design_variables_mapper["wind"]]["upper"]
            wind_bounds = (wind_lb,wind_ub)
        if "pv" in re_plant_type:
            pv_lb = self.design_variables_info[self.design_variables_mapper["pv"]]["lower"]
            pv_ub = self.design_variables_info[self.design_variables_mapper["pv"]]["upper"]
            pv_bounds = (pv_lb,pv_ub)
        if "wind-pv" in re_plant_type:
            return (wind_bounds,pv_bounds)
        else:
            if "wind" in re_plant_type:
                return wind_bounds
            if "pv" in re_plant_type:
                return pv_bounds
    
    def add_full_simplex(self,full_simplex):
        self.full_simplex = full_simplex
    
    def save_full_simplex(self,output_dir):
        output_filepath = self.get_full_simplex_filename(output_dir)
        pd.DataFrame(self.full_simplex).T.to_pickle(output_filepath)
    
    def get_full_simplex_filename(self,output_dir):
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}".format(self.id,self.latitude,self.longitude,self.state.replace(" ","")))
        full_simplex_filename =  output_filepath_root + "--Simplex.pkl"
        return full_simplex_filename
        
    def get_extra_data_simplex_filename(self,output_dir):
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}".format(self.id,self.latitude,self.longitude,self.state.replace(" ","")))
        full_simplex_filename =  output_filepath_root + "--ParametricSweep_Results.pkl"
        return full_simplex_filename
    # def add_optimization_tracker_results(self,re_plant_type,merit_figure,keys,vals):
    #     temp_df = pd.DataFrame(vals,columns = [re_plant_type + merit_figure],index=keys).T
    #     self.optimization_tracker = pd.concat([self.optimization_tracker,temp_df],axis=0)
    
    def add_optimization_res(self,optimization_res,re_plant_desc,merit_figure):
        if len(self.optimization_tracker)==0:
            self.optimization_tracker = pd.Series(optimization_res,name=re_plant_desc + ": " + merit_figure)
        else:
            temp = pd.Series(optimization_res,name=re_plant_desc + ": " + merit_figure)
        
            self.optimization_tracker = pd.concat([temp,self.optimization_tracker],axis=1)
    
    def save_optimization_results(self,output_dir):
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}".format(self.id,self.latitude,self.longitude,self.state.replace(" ","")))
        output_filepath =  output_filepath_root + "--Optimization_Outputs.pkl"
        self.optimization_tracker.to_pickle(output_filepath)

    def add_optimization_simplex_results(self,re_plant_type,merit_figure,keys,vals): 
        temp_df = pd.DataFrame(vals,columns = [re_plant_type + merit_figure],index=keys).T
        self.optimization_simplex = pd.concat([self.optimization_simplex,temp_df],axis=0)

    def save_optimization_simplex_results(self,output_dir):
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}".format(self.id,self.latitude,self.longitude,self.state.replace(" ","")))
        output_filepath =  output_filepath_root + "--Optimized_DesignResults.pkl"
        self.optimization_simplex.to_pickle(output_filepath)

    def get_final_simplex_for_hybrid_plant(self,re_plant_desc,merit_figure):
        if "battery" in re_plant_desc:
            data = self.full_simplex[self.full_simplex["battery"]==True]
        else:
            data = self.full_simplex[self.full_simplex["battery"]==False]
        n = 2
        cols = ["wind","pv"]
        sorted_df = data.sort_values(merit_figure,ascending=True)
        initial_simplex_df = sorted_df.iloc[:n+1]
        initial_simplex = np.zeros((n+1,n))
        
        for i,re_type in enumerate(cols):
            col = self.design_variables_mapper[re_type]
            initial_simplex[:,i] = np.array(initial_simplex_df[col].to_list())
        return initial_simplex,cols
    def get_hybrid_sizes_for_making_full_simplex(self):
        unique_wind_sizes = []
        unique_wind_sizes += self.design_variables_info[self.design_variables_mapper["wind"]]["extra_simplex_sizes"]
        unique_wind_sizes += self.design_variables_info[self.design_variables_mapper["wind"]]["initial_simplex_sizes"]

        unique_pv_sizes = []
        unique_pv_sizes += self.design_variables_info[self.design_variables_mapper["pv"]]["extra_simplex_sizes"]
        unique_pv_sizes += self.design_variables_info[self.design_variables_mapper["pv"]]["initial_simplex_sizes"]
        
        wind_sizes_list = np.zeros(len(unique_wind_sizes)*len(unique_pv_sizes))
        pv_sizes_list = np.zeros(len(unique_wind_sizes)*len(unique_pv_sizes))
        cnt = 0
        for wind_size in unique_wind_sizes:
            for pv_size in unique_pv_sizes:
                wind_sizes_list[cnt] = wind_size
                pv_sizes_list[cnt] = pv_size
                cnt +=1
        return wind_sizes_list,pv_sizes_list
