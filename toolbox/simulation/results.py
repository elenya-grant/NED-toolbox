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

    # lcoh_pf_config: pd.Series = field(init = False)
    # lcoh_cost_breakdown: pd.DataFrame = field(init = False)
    lcoh_pf_config: Optional[dict] = field(default = {})
    lcoh_cost_breakdown: Optional[pd.DataFrame] = field(default = None)

    def __attrs_post_init__(self):
        
        self.lcoh_cost_breakdown = self.lcoh_pf.get_cost_breakdown()
        
        self.lcoh_pf_config = {"params":self.lcoh_pf.vals,
        "capital_items":self.lcoh_pf.capital_items,
        "fixed_costs":self.lcoh_pf.fixed_costs,
        "feedstocks":self.lcoh_pf.feedstocks,
        "incentives":self.lcoh_pf.incentives,
        "LCOH":self.lcoh_pf.LCO}
        # self.lcoh_pf_config = pd.Series(lcoh_pf_config)

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

    # lcoe_pf_config: pd.Series = field(init = False)
    # lcoe_cost_breakdown: pd.DataFrame = field(init = False)
    lcoe_pf_config: Optional[dict] = field(default = {})
    lcoe_cost_breakdown: Optional[pd.DataFrame] = field(default = None)

    def __attrs_post_init__(self):
        
        self.lcoe_cost_breakdown = self.lcoe_pf.get_cost_breakdown()
        
        self.lcoe_pf_config = {"params":self.lcoe_pf.vals,
        "capital_items":self.lcoe_pf.capital_items,
        "fixed_costs":self.lcoe_pf.fixed_costs,
        "feedstocks":self.lcoe_pf.feedstocks,
        "incentives":self.lcoe_pf.incentives,
        "LCOE":self.lcoe_pf.LCO}
        # self.lcoe_pf_config = pd.Series(lcoe_pf_config)
        # self.lcoe_pf_config = pd.Series(lcoe_pf_config)
    
    def get_lcoe_summary(self):
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="lcoe_pf"}
        return summary
    
    def update_re_plant_type(self,re_plant_type:str):
        self.re_plant_type = re_plant_type

    def update_atb_scenario(self,atb_scenario:str):
        self.atb_scenario = atb_scenario


@define
class FinanceResults(FromDictMixin):
    capex_breakdown: dict
    opex_breakdown_annual: dict
    
    atb_year: int
    atb_scenario: Optional[str]
    policy_scenario: Union[str,int]

    re_plant_type: Optional[str]
    h2_storage_type: str #= field(init = False)
    h2_transport_type: str #= field(init = False)

    def update_re_plant_type(self,re_plant_type:str):
        self.re_plant_type = re_plant_type

    def update_atb_scenario(self,atb_scenario:str):
        self.atb_scenario = atb_scenario

    def get_finance_summary(self):
        d = self.as_dict()
        # summary = {k:v for k,v in d.items() if k!="lcoe_pf"}
        return d #summary
        
    # pv_capacity_MWac: Union[float,int]
    # wind_capacity_MWac: Union[float,int]
    # battery_capacity_MWdc: Optional[Union[float,int]] = field(default = 0)
    # battery_capacity_MWhdc: Optional[Union[float,int]] = field(default = 0)

@define
class PhysicsResults(FromDictMixin):
    hopp_results: dict
    electrolyzer_physics_results: dict

    h2_storage_results: Optional[dict] = field(default = None)
    h2_transport_pipe_results: Optional[Union[dict,pd.DataFrame]] = field(default = None)
    h2_transport_compressor_results: Optional[dict] = field(default = None)

    # renewables_summary: dict = field(init = False)
    # renewable_plant_design_type: str = field(init = False)
    renewables_summary: Optional[dict] = field(default = {})
    renewable_plant_design_type: Optional[str] = field(default = "")

    # re_plant_type: str = field(init = False)
    # h2_storage_type: str = field(init = False)
    # h2_transport_type: str = field(init = False)
    re_plant_type: Optional[str] = field(default = "")
    h2_storage_type: Optional[str] = field(default = "")
    h2_transport_type: Optional[str] = field(default = "")

    # h2_results: dict = field(init=False)
    # electrolyzer_LTA: pd.DataFrame() = field(init=False)
    h2_results: Optional[dict] = field(default = {})
    electrolyzer_LTA: Optional[pd.DataFrame] = field(default = None)
    timeseries: Optional[dict] = field(default = {})
    def __attrs_post_init__(self):
        self.renewables_summary, self.renewable_plant_design_type = summarize_renewables_info(self.hopp_results)
        float_keys = [k for k in self.electrolyzer_physics_results["H2_Results"].keys() if isinstance(self.electrolyzer_physics_results["H2_Results"][k],(int,float))]
        self.h2_results = {k:self.electrolyzer_physics_results["H2_Results"][k] for k in float_keys}
        self.electrolyzer_LTA = self.electrolyzer_physics_results["H2_Results"]["Performance Schedules"]
        h2_hourly = self.electrolyzer_physics_results["H2_Results"]["Hydrogen Hourly Production [kg/hr]"]
        self.h2_results.update({"Max H2 Production [kg/hr]":max(h2_hourly)})
        self.h2_results.update({"Avg H2 Production [kg/hr]":np.nanmean(h2_hourly)})

        self.timeseries.update({"H2 Production [kg/hr]":h2_hourly})
        self.timeseries.update({"HOPP Power Production [kW]":np.array(self.hopp_results["combined_hybrid_power_production_hopp"])})
        self.timeseries.update({"HOPP Curtailment [kW]":self.hopp_results['combined_hybrid_curtailment_hopp']})
        self.timeseries.update({"Power to Electrolyzer [kW]":self.electrolyzer_physics_results["power_to_electrolyzer_kw"]})
        if "wind" in self.renewable_plant_design_type:
            
            self.timeseries.update({"Wind Generation":self.hopp_results["hybrid_plant"].wind.generation_profile})
            
        if "pv" in self.renewable_plant_design_type:
            
            self.timeseries.update({"PV Generation":self.hopp_results["hybrid_plant"].pv.generation_profile})

        if "hydrogen_storage_soc" in self.h2_storage_results:
            soc = self.h2_storage_results.pop("hydrogen_storage_soc")
            self.timeseries.update({"H2 Storage SOC [kg]":soc})
        

        self.hopp_results = {} #remove big data

        if isinstance(self.h2_transport_pipe_results,pd.DataFrame):
            self.h2_transport_pipe_results = self.h2_transport_pipe_results.T.to_dict()[0]
    def update_re_plant_type(self,re_plant_type:str):
        self.re_plant_type = re_plant_type

    def update_h2_design_scenario(self,h2_storage_type:str,h2_transport_type:str):
        self.h2_storage_type = h2_storage_type
        self.h2_transport_type = h2_transport_type
    
    def get_physics_summary(self):
        #TODO: update this
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="hopp_results"}
        summary = {k:v for k,v in summary.items() if k!="electrolyzer_physics_results"}
        return summary
        # if self.h2_transport_pipe_results is not None:
        #     h2_storage_transport_design_type = ""
        #     if isinstance(self.h2_transport_pipe_results,pd.DataFrame):
        #         h2_transport_type = "none"
        #         self.h2_transport_pipe_results = {}

        # if self.h2_storage_results is not None:
        #     self.h2_storage_results["h2_storage_max_fill_rate_kg_hr"]
        #     self.h2_storage_results["h2_storage_capacity_kg"]


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
    extra_desc: Optional[str] = field(default = "")
    # n_incentive_options: int = field(default = 1)
    # n_plant_design_types: int = field(default = 1)
    # n_atb_scenarios: int = field(default = 1)
    # n_storage_types: int = field(default = 1)

    # n_lcoh_results: int = field(init=False)
    # n_lcoe_results: int = field(init=False)
    # n_opex_capex_breakdown_results: int = field(init = False)
    # n_physics_results: int = field(init = False)

    LCOH_Res: List[LCOHResults] = field(init = False)
    LCOE_Res: List[LCOEResults] = field(init = False)
    Finance_Res: List[FinanceResults] = field(init = False)
    Physics_Res: List[PhysicsResults] = field(init = False)
    
    # saved_num: int = field(init = False)
    
    
    def __attrs_post_init__(self):
        # self.n_lcoh_results = self.n_incentive_options*self.n_plant_design_types*self.n_atb_scenarios*self.n_storage_types
        # self.n_lcoe_results = self.n_incentive_options*self.n_plant_design_types*self.n_atb_scenarios
        # self.n_opex_capex_breakdown_results = self.n_plant_design_types*self.n_atb_scenarios*self.n_storage_types
        # self.n_physics_results = self.n_plant_design_types*self.n_storage_types

        self.LCOH_Res = []
        self.LCOE_Res = []
        self.Finance_Res = []
        self.Physics_Res = []

        # self.saved_num = 0

    def add_LCOH_Results(self,lcoh_res:LCOHResults):
        self.LCOH_Res.append(lcoh_res)

    def add_LCOE_Results(self,lcoe_res:LCOEResults):
        self.LCOE_Res.append(lcoe_res)

    def add_Finance_Results(self,fin_res:FinanceResults):
        self.Finance_Res.append(fin_res)

    def add_Physics_Results(self,phy_res:PhysicsResults):
        self.Physics_Res.append(phy_res)

    def make_LCOH_summary_results(self):
        temp = [pd.Series(self.LCOH_Res[i].get_lcoh_summary()) for i in range(len(self.LCOH_Res))]
        return pd.DataFrame(temp)
    
    def make_LCOE_summary_results(self):
        temp = [pd.Series(self.LCOE_Res[i].get_lcoe_summary()) for i in range(len(self.LCOE_Res))]
        return pd.DataFrame(temp)

    def make_Physics_summary_results(self):
        temp = [pd.Series(self.Physics_Res[i].get_physics_summary()) for i in range(len(self.Physics_Res))]
        return pd.DataFrame(temp)
    
    def make_Finance_summary_results(self):
        temp = [pd.Series(self.Finance_Res[i].get_finance_summary()) for i in range(len(self.Finance_Res))]
        return pd.DataFrame(temp)
        
    def write_outputs(self,output_dir:str,save_separately = False):
        # self.saved_num +=1
        # output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}-{}_{}".format(self.site.id,self.site.latitude,self.site.longitude,self.site.state,self.site.county,self.extra_desc))
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}_{}_{}".format(self.site.id,self.site.latitude,self.site.longitude,self.site.state.replace(" ",""),self.atb_year,self.extra_desc))
        site_res = pd.Series(self.site.as_dict())
        lcoh_res = self.make_LCOH_summary_results()
        lcoe_res = self.make_LCOE_summary_results()
        phys_res = self.make_Physics_summary_results()
        fin_res = self.make_Finance_summary_results()

        if save_separately:
            site_res.to_pickle(output_filepath_root + "--Site_Info.pkl")
            lcoh_res.to_pickle(output_filepath_root + "--LCOH_Results.pkl")
            lcoe_res.to_pickle(output_filepath_root + "--LCOE_Results.pkl")
            phys_res.to_pickle(output_filepath_root + "--Physics_Results.pkl")
            fin_res.to_pickle(output_filepath_root + "--Financial_Results.pkl")
        else:
            res = {"Site":site_res,"LCOH":lcoh_res,"LCOE":lcoe_res,"Physics":phys_res,"Financials":fin_res}
            pd.Series(res).to_pickle(output_filepath_root + "--Results.pkl")