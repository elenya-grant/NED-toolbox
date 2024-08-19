import os
from typing import Optional, Union
import warnings
import numpy as np
import pandas as pd
from attrs import define, field
from hopp.utilities.validators import contains, range_val
from toolbox.simulation.ned_site import Site
from ProFAST import ProFAST
from toolbox.simulation.ned_simulation_outputs import summarize_renewables_info
from typing import List, Sequence, Optional, Union
from toolbox.simulation.ned_base import BaseClassNed
from hopp.type_dec import FromDictMixin

@define
class LCOHResults(FromDictMixin):
    lcoh_pf: ProFAST
    lcoh: float

    atb_year: int
    atb_scenario: Optional[str]
    policy_scenario: Union[str,int]

    re_plant_type: Optional[str]
    h2_storage_type: str
    h2_transport_design: str

    lcoh_pf_config: pd.Series = field(init = False)
    lcoh_cost_breakdown: pd.DataFrame = field(init = False)

    def __attrs_post_init__(self):
        
        self.lcoh_cost_breakdown = self.lcoh_pf.get_cost_breakdown()
        
        lcoh_pf_config = {"params":self.lcoh_pf.vals,
        "capital_items":self.lcoh_pf.capital_items,
        "fixed_costs":self.lcoh_pf.fixed_costs,
        "feedstocks":self.lcoh_pf.feedstocks,
        "incentives":self.lcoh_pf.incentives,
        "LCOH":self.lcoh_pf.LCO}
        self.lcoh_pf_config = pd.Series(lcoh_pf_config)

    def get_lcoh_summary(self):
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="lcoh_pf"}
        return summary

    def update_re_plant_type(self,re_plant_type:str):
        self.re_plant_type = re_plant_type

    def update_atb_scenario(self,atb_scenario:str):
        self.atb_scenario = atb_scenario
        

@define
class LCOEResults(FromDictMixin):
    lcoe_pf: ProFAST
    lcoe: float

    atb_year: int
    policy_scenario: Union[str,int]
    atb_scenario: Optional[str]
    re_plant_type: Optional[str]

    lcoe_pf_config: pd.Series = field(init = False)
    lcoe_cost_breakdown: pd.DataFrame = field(init = False)

    def __attrs_post_init__(self):
        
        self.lcoe_cost_breakdown = self.lcoe_pf.get_cost_breakdown()
        
        lcoe_pf_config = {"params":self.lcoe_pf.vals,
        "capital_items":self.lcoe_pf.capital_items,
        "fixed_costs":self.lcoe_pf.fixed_costs,
        "feedstocks":self.lcoe_pf.feedstocks,
        "incentives":self.lcoe_pf.incentives,
        "LCOE":self.lcoe_pf.LCO}
        self.lcoe_pf_config = pd.Series(lcoe_pf_config)
    
    def get_lcoe_summary(self):
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="lcoe_pf"}
        return summary
    
    def update_re_plant_type(self,re_plant_type:str):
        self.re_plant_type = re_plant_type

    def update_atb_scenario(self,atb_scenario:str):
        self.atb_scenario = atb_scenario


@define
class FinanceResults:
    capex_breakdown: dict
    opex_breakdown_annual: dict
    
    atb_year: int
    atb_scenario: str
    policy_scenario: Union[str,int]

    re_plant_type: str
    h2_storage_transport_design: int

    # pv_capacity_MWac: Union[float,int]
    # wind_capacity_MWac: Union[float,int]
    # battery_capacity_MWdc: Optional[Union[float,int]] = field(default = 0)
    # battery_capacity_MWhdc: Optional[Union[float,int]] = field(default = 0)

@define
class PhysicsResults:
    hopp_results: dict
    electrolyzer_physics_results: dict

    h2_storage_results: Optional[dict] = field(default = None)
    h2_transport_pipe_results: Optional[Union[dict,pd.DataFrame]] = field(default = None)
    h2_transport_compressor_results: Optional[dict] = field(default = None)

    renewables_summary: dict = field(init = False)
    renewable_plant_design_type: str = field(init = False)

    h2_storage_type: str = field(init = False)
    h2_storage_transport_type: str = field(init = False)

    h2_results: dict = field(init=False)
    electrolyzer_LTA: pd.DataFrame() = field(init=False)
    def __attrs_post_init__(self):
        self.renewables_summary, self.renewable_plant_design_type = summarize_renewables_info(self.hopp_results)
        float_keys = [k for k in self.electrolyzer_physics_results["H2_Results"].keys() if isinstance(self.electrolyzer_physics_results["H2_Results"][k],(int,float))]
        self.h2_results = {k:self.electrolyzer_physics_results["H2_Results"][k] for k in float_keys}
        self.electrolyzer_LTA = self.electrolyzer_physics_results["H2_Results"]["Performance Schedules"]
        h2_hourly = self.electrolyzer_physics_results["H2_Results"]["Hydrogen Hourly Production [kg/hr]"]
        self.h2_results.update({"Max H2 Production [kg/hr]":max(h2_hourly)})
        self.h2_results.update({"Avg H2 Production [kg/hr]":np.nanmean(h2_hourly)})
        
        if self.h2_transport_pipe_results is not None:
            h2_storage_transport_design_type = ""
            if isinstance(self.h2_transport_pipe_results,pd.DataFrame):
                h2_transport_type = "none"
                self.h2_transport_pipe_results = {}

        if self.h2_storage_results is not None:
            self.h2_storage_results["h2_storage_max_fill_rate_kg_hr"]
            self.h2_storage_results["h2_storage_capacity_kg"]


# @define
# class RenewablesResults:
#     hopp_config: dict = field(init=False)


@define
class NedOutputs(BaseClassNed):
    site: Site
    sweep_name: str = field(validator=contains(['offgrid-baseline','gridonly-baseline','offgrid-optimized']))
    # renewable_plant_design_type: str = field(validator=contains(['wind','wind-pv','wind-battery','wind-pv-battery','pv','pv-battery']))
    atb_year: int = field(validator=range_val(2020.,2050.))

    subsweep_name: Optional[str] = field(default = None) #"oversized,undersized,equal-sized"
    
    n_incentive_options: int = field(default = 1)
    n_plant_design_types: int = field(default = 1)
    n_atb_scenarios: int = field(default = 1)
    n_storage_types: int = field(default = 1)

    n_lcoh_results: int = field(init=False)
    n_lcoe_results: int = field(init=False)
    n_opex_capex_breakdown_results: int = field(init = False)
    n_physics_results: int = field(init = False)

    LCOH_Res: List[LCOHResults] = field(init = False)
    LCOE_Res: List[LCOEResults] = field(init = False)
    Finance_Res: List[FinanceResults] = field(init = False)
    Physics_Res: List[PhysicsResults] = field(init = False)
    
    
    def __attrs_post_init__(self):
        self.n_lcoh_results = self.n_incentive_options*self.n_plant_design_types*self.n_atb_scenarios*self.n_storage_types
        self.n_lcoe_results = self.n_incentive_options*self.n_plant_design_types*self.n_atb_scenarios
        self.n_opex_capex_breakdown_results = self.n_plant_design_types*self.n_atb_scenarios*self.n_storage_types
        self.n_physics_results = self.n_plant_design_types*self.n_storage_types

        self.LCOH_Res = []
        self.LCOE_Res = []
        self.Finance_Res = []
        self.Physics_Res = []

    def add_LCOH_Results(self,lcoh_res:LCOHResults):
        self.LCOH_Res.append(lcoh_res)

    def add_LCOE_Results(self,lcoe_res:LCOEResults):
        self.LCOE_Res.append(lcoe_res)

    def add_Finance_Results(self,fin_res:FinanceResults):
        self.Finance_Res.append(fin_res)

    def add_Physics_Results(self,phy_res:PhysicsResults):
        self.Physics_Res.append(phy_res)

    def make_LCOH_summary_results(self):
        pass