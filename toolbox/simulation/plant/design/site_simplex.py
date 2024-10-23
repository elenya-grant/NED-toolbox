from hopp.simulation.base import BaseClass
from toolbox.simulation.ned_base import BaseClassNed
from typing import Iterable, List, Sequence, Optional, Union, TYPE_CHECKING

import numpy as np
from hopp.type_dec import hopp_float_type
from hopp.utilities.validators import contains, range_val, gt_zero
from attrs import define, field
from hopp.simulation.technologies.pv.pv_plant import PVConfig
import copy
from toolbox.utilities.yaml_tools import write_yaml
import os
import pandas as pd

# @define
# class HybridSimplex(BaseClassNed):
#     bound_simplex: pd.DataFrame() = field(default = None)
#     unique_simplex: pd.DataFrame() = field(default = None)
#     initial_simplex: Optional[pd.DataFrame()] = field(default = None)
#     merit_figures: List[str] = field(default = [])
#     simplex_index: List[str] = field(default = [])
#     simplex_x_names: List[str] = field(default = [])
#     simplex_ynames: List[str] = field(default = [])
    


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



# @define
# class SiteSimplex(BaseClassNed):
#     latitude: hopp_float_type = field(converter = hopp_float_type)
#     longitude: hopp_float_type = field(converter = hopp_float_type)
#     # latitude: float = field(validator=gt_zero)
#     # longitude: float = field(validator=gt_zero)
    
#     distance_to_salt_cavern: float = field(converter = hopp_float_type)
#     distance_to_rock_cavern: float = field(converter = hopp_float_type)
#     # balancing_area_id: int = field(validator=range_val(1,134))

#     balancing_area: Optional[str] = field(default = None)
#     # resource_year: Optional[int] = field(default = None, validator=range_val(2007, 2013))

#     state: Optional[str] = field(default=None)
#     county: Optional[str] = field(default=None)
#     CountyFP: Optional[float] = field(default=None)
#     id: Optional[float] = field(default=None)

#     rock_cavern_loc: Optional[str] = field(default=None)
#     salt_cavern_loc: Optional[str] = field(default=None)
#     feedstock_region: str = field(default="US Average", validator=contains(['East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central','US Average']))
    
#     simplex_data: pd.DataFrame() = field(default = None) #TODO: make optional
#     simplex_case_info: dict() = field(default = None) #optimization_config["driver"]["design_of_simplex"]
#     design_variables_info: dict() = field(default = None) #optimization_config["design_variables"]

#     merit_figure: str = field(default="lcoh") #optimization_config["merit_figure"]
#     design_variables: dict() = field(default = None)

#     full_simplex: pd.DataFrame() = field(default = None)
#     opt_results: pd.DataFrame() = field(default = None)
#     # wind_solar_simplex: Optional[pd.DataFrame] = field(default = None)
#     # solar_simplex: Optional[pd.DataFrame] = field(default = None)
#     # wind_simplex: Optional[pd.DataFrame] = field(default = None)
    
#     def __attrs_post_init__(self):
#         levels_to_drop = ["latitude","longitude","state","Case"]
#         self.simplex_data = self.simplex_data.droplevel(levels_to_drop)
        
#         self.design_variables_info = {k:self.design_variables_info[k] for k in self.design_variables_info.keys() if self.design_variables_info[k]["flag"]}
#         self.design_variables = {self.design_variables_info[k]["re_plant"]: self.design_variables_info[k] for k in self.design_variables_info.keys()}
#     def get_simplex_for_plant_design(self,re_plant_type):
#         #assumes we arent optimizing battery capacity
#         simplex_cases = []
#         simplex_cols = []
#         simplex_newcols = []
#         simplex_multipliers = []
#         if "wind" in re_plant_type:
#             # simplex_cases += ["wind"]
#             # simplex_cols += [k for k in self.simplex_data.columns.to_list() if "wind" in k.lower()]
#             simplex_cols += [self.design_variables["wind"]["simplex_keyname"]]
#             simplex_multipliers +=[self.design_variables["wind"]["simplex_key_multiplier"]]
#             simplex_newcols += ["wind"]
#             if "battery" in re_plant_type:
#                 simplex_cases += ["wind-battery"]
#             else:
#                 simplex_cases += ["wind"]
#         if "pv" in re_plant_type:
#             # simplex_cases += ["pv"]
#             # simplex_cols += [k for k in self.simplex_data.columns.to_list() if "pv" in k.lower()]
#             simplex_cols += [self.design_variables["pv"]["simplex_keyname"]]
#             simplex_multipliers +=[self.design_variables["pv"]["simplex_key_multiplier"]]
#             simplex_newcols += ["pv"]
#             if "battery" in re_plant_type:
#                 simplex_cases += ["pv-battery"]
#             else:
#                 simplex_cases += ["pv"]
#         if "pv" in re_plant_type and "wind" in re_plant_type:
#             # simplex_cases += ["wind-pv"]
            
#             if "battery" in re_plant_type:
#                 simplex_cases += ["wind-pv-battery"]
#             else:
#                 simplex_cases += ["wind-pv"]
#         simplex_cols += [k for k in self.simplex_data.columns.to_list() if self.merit_figure in k.lower()]
#         simplex_multipliers +=[1]
#         simplex_newcols += [self.merit_figure]
#         simplex = self.simplex_data.loc[simplex_cases][simplex_cols]*np.array(simplex_multipliers)
#         simplex = simplex.rename(columns=dict(zip(simplex_cols,simplex_newcols)))
#         return simplex

#     def get_bounds_for_plant_design(self,re_plant_type):
#         if "wind" in re_plant_type:
#             wind_bounds = (self.design_variables["wind"]["lower"],self.design_variables["wind"]["upper"])
#         if "pv" in re_plant_type:
#             solar_bounds = (self.design_variables["pv"]["lower"],self.design_variables["pv"]["upper"])
#         if "wind-pv" in re_plant_type:
#             bnds = (wind_bounds,solar_bounds)
#         else:
#             if "wind" in re_plant_type:
#                 bnds = wind_bounds
#             if "pv" in re_plant_type:
#                 bnds = solar_bounds
#         return bnds
    
#     # def get_inputs_for_optimization(self,re_plant_type):
#     #     simplex_df = self.get_simplex_for_plant_design(re_plant_type)
#     #     bounds = self.get_bounds_for_plant_design(re_plant_type)
#     #     x_cols = [k for k in simplex_df.columns.to_list() if k!= self.merit_figure]
#     #     n = len(x_cols)
#     #     initial_simplex_x0 = np.zeros((len(simplex_df),n))
#     #     simplex_df.sort_values("lcoh")
#     #     for ix,x in enumerate(x_cols):
#     #         vals = np.array(simplex_df[x].to_list())
#     #         lb = min(bounds[ix])
#     #         ub = max(bounds[ix])
#     #         usable_vals_i_lb = np.argwhere(vals>lb).flatten()
#     #         usable_vals_i_ub = np.argwhere(vals<ub).flatten()
#     #         usable_vals_i = [i for i in usable_vals_i_lb if i in usable_vals_i_ub]
#     #         simplex_df = simplex_df.iloc[usable_vals_i]
        
#     #     []
#     #     simplex_df.sort_values("lcoh",ascending=False)
#     #     []
#     def add_case_to_simplex(self,wind_size_mw,pv_size_mwdc,include_battery,lcoh):
#         re_plant_desc = ""
#         if wind_size_mw>0:
#             re_plant_desc += "wind-"
#         else:
#             re_plant_desc += ""
#         if pv_size_mwdc>0:
#             re_plant_desc += "pv-"
#         else:
#             re_plant_desc += ""
#         if include_battery:
#             re_plant_desc += "battery"
#         else:
#             re_plant_desc = re_plant_desc.strip("-")
        
        
#         temp = pd.DataFrame(dict(zip(["wind","pv","lcoh","RE Plant Design"],[wind_size_mw,pv_size_mwdc,lcoh,re_plant_desc])),index=[0])
#         temp = temp.set_index(keys = "RE Plant Design",drop=True)
#         self.full_simplex = pd.concat([self.full_simplex,temp],axis=0)

#     def update_simplex_for_bounds(self,simplex_bounds):
#         wind_colname = [c for c in simplex_bounds.columns.to_list() if "wind" in c]
#         solar_colname = [c for c in simplex_bounds.columns.to_list() if "pv" in c]
#         battery_colname = [c for c in simplex_bounds.columns.to_list() if "battery" in c]
#         mapper = {wind_colname[0]:"wind",solar_colname[0]:"pv",battery_colname[0]:"battery"}
#         simplex_bounds = simplex_bounds.rename(columns = mapper)
#         plant_descriptions = []
#         for i in range(len(simplex_bounds)):
#             re_plant_desc = ""
#             if simplex_bounds.iloc[i]["wind"]>0:
#                 re_plant_desc += "wind-"
#             else:
#                 re_plant_desc += ""
#             if simplex_bounds.iloc[i]["pv"]>0:
#                 re_plant_desc += "pv-"
#             else:
#                 re_plant_desc += ""
#             if simplex_bounds.iloc[i]["battery"]:
#                 re_plant_desc += "battery"
#             else:
#                 re_plant_desc = re_plant_desc.strip("-")
#             plant_descriptions.append(re_plant_desc)
        
#         simplex_bounds["RE Plant Design"] = plant_descriptions
#         simplex_bounds = simplex_bounds.set_index(keys = "RE Plant Design",drop=True)
#         simplex_bounds = simplex_bounds.drop(columns="battery")
#         init_simplex_battery = self.get_simplex_for_plant_design("wind-pv-battery")
#         init_simplex_nobattery = self.get_simplex_for_plant_design("wind-pv")
#         if self.full_simplex is None:
#             self.full_simplex = pd.concat([simplex_bounds,init_simplex_nobattery,init_simplex_battery],axis=0)
#         else:
#             self.full_simplex = pd.concat([simplex_bounds,self.full_simplex],axis=0)

#         # full_init_simplex.rename(columns={"wind":"wind_size_mw","pv":"pv_size_mwdc"})

#     def get_final_simplex_for_plant(self,re_plant_desc):
#         if "wind-pv" in re_plant_desc:
#             n = 2
#         else:
#             n = 1
#         cols = re_plant_desc.split("-")
#         cols = [c for c in cols if c!="battery"]
#         sorted_df = self.full_simplex.loc[re_plant_desc].sort_values(self.merit_figure,ascending=True)
#         initial_simplex_df = sorted_df.iloc[:n+1]
#         # initial_simplex = initial_simplex_df[cols].values

#         initial_simplex = np.zeros((n+1,n))
#         for i,col in enumerate(cols):
#             initial_simplex[:,i] = np.array(initial_simplex_df[col].to_list())
#         # initial_simplex[:,1] = top_wind
#         # np.shape(initial_simplex_df[["wind","pv"]].values)
#         return initial_simplex,cols
    
#     def add_optimization_results(self,res,re_plant_desc):
#         temp = pd.Series(res,name=re_plant_desc)
#         self.opt_results = pd.concat([self.opt_results,temp],axis=1)

#     def save_simplex(self,output_dir):
#         output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}".format(self.id,self.latitude,self.longitude,self.state.replace(" ","")))
        
#         self.full_simplex.to_pickle(output_filepath_root + "--Simplex_Results.pkl")
