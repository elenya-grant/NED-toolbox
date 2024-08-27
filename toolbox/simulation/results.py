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

    # def __attrs_post_init__(self):
        
    #     self.lcoh_cost_breakdown = self.lcoh_pf.get_cost_breakdown()
        
    #     self.lcoh_pf_config = {"params":self.lcoh_pf.vals,
    #     "capital_items":self.lcoh_pf.capital_items,
    #     "fixed_costs":self.lcoh_pf.fixed_costs,
    #     "feedstocks":self.lcoh_pf.feedstocks,
    #     "incentives":self.lcoh_pf.incentives,
    #     "LCOH":self.lcoh_pf.LCO}

    def get_lcoh_summary(self):
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="lcoh_pf"}
        summary = {k:v for k,v in summary.items() if k!="lcoh_pf_config"}
        summary = {k:v for k,v in summary.items() if k!="lcoh_cost_breakdown"}
        return summary

    def get_lcoh_detailed_results(self, save_cost_breakdown = False):
        self.lcoh_cost_breakdown = self.lcoh_pf.get_cost_breakdown()
        
        self.lcoh_pf_config = {"params":self.lcoh_pf.vals,
        "capital_items":self.lcoh_pf.capital_items,
        "fixed_costs":self.lcoh_pf.fixed_costs,
        "feedstocks":self.lcoh_pf.feedstocks,
        "incentives":self.lcoh_pf.incentives,
        "LCOH":self.lcoh_pf.LCO}

        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="lcoh_pf"}
        if not save_cost_breakdown:
            summary = {k:v for k,v in summary.items() if k!="lcoh_cost_breakdown"}

        # detailed_keys = ["lcoh_pf_config","lcoh_cost_breakdown"]
        # summary = {k:v for k,v in d.items() if k in detailed_keys}
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

    # def __attrs_post_init__(self):
        
        # self.lcoe_cost_breakdown = self.lcoe_pf.get_cost_breakdown()
        
        # self.lcoe_pf_config = {"params":self.lcoe_pf.vals,
        # "capital_items":self.lcoe_pf.capital_items,
        # "fixed_costs":self.lcoe_pf.fixed_costs,
        # "feedstocks":self.lcoe_pf.feedstocks,
        # "incentives":self.lcoe_pf.incentives,
        # "LCOE":self.lcoe_pf.LCO}
        
    
    def get_lcoe_summary(self):
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="lcoe_pf"}
        summary = {k:v for k,v in summary.items() if k!="lcoe_pf_config"}
        summary = {k:v for k,v in summary.items() if k!="lcoe_cost_breakdown"}
        return summary
    
    def get_lcoe_detailed_results(self, save_cost_breakdown = False):
        self.lcoe_cost_breakdown = self.lcoe_pf.get_cost_breakdown()
        
        self.lcoe_pf_config = {"params":self.lcoe_pf.vals,
        "capital_items":self.lcoe_pf.capital_items,
        "fixed_costs":self.lcoe_pf.fixed_costs,
        "feedstocks":self.lcoe_pf.feedstocks,
        "incentives":self.lcoe_pf.incentives,
        "LCOE":self.lcoe_pf.LCO}
        
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="lcoe_pf"}
        if not save_cost_breakdown:
            summary = {k:v for k,v in summary.items() if k!="lcoe_cost_breakdown"}
        # detailed_keys = ["lcoe_pf_config","lcoe_cost_breakdown"]
        # summary = {k:v for k,v in d.items() if k in detailed_keys}
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
    h2_design_results: Optional[dict] = field(default = {})

    def __attrs_post_init__(self):
        self.timeseries = {}
        self.h2_results = {}
        self.renewables_summary = {}
        self.h2_design_results = {}
        self.electrolyzer_LTA = pd.DataFrame()

        self.renewables_summary, self.renewable_plant_design_type = summarize_renewables_info(self.hopp_results["hybrid_plant"])
        float_keys = [k for k in self.electrolyzer_physics_results["H2_Results"].keys() if isinstance(self.electrolyzer_physics_results["H2_Results"][k],(int,float))]
        self.h2_results = {k:self.electrolyzer_physics_results["H2_Results"][k] for k in float_keys}
        self.electrolyzer_LTA = self.electrolyzer_physics_results["H2_Results"]["Performance Schedules"]
        h2_hourly = self.electrolyzer_physics_results["H2_Results"]["Hydrogen Hourly Production [kg/hr]"]
        self.h2_results.update({"Max H2 Production [kg/hr]":max(h2_hourly)})
        self.h2_results.update({"Avg H2 Production [kg/hr]":np.nanmean(h2_hourly)})

        self.timeseries.update({"H2 Production [kg/hr]":h2_hourly})
        self.timeseries.update({"HOPP Power Production [kW]":np.array(self.hopp_results["combined_hybrid_power_production_hopp"])})
        self.timeseries.update({"Power to Electrolyzer [kW]":self.electrolyzer_physics_results["power_to_electrolyzer_kw"]})
        
        original_gen = np.zeros(len(h2_hourly))
        if sum(self.hopp_results['combined_hybrid_curtailment_hopp'])<100:
            self.timeseries.update({"HOPP Curtailment [kW]":self.hopp_results['combined_hybrid_curtailment_hopp'][:len(h2_hourly)]})
        
        if "wind" in self.renewable_plant_design_type:
            
            self.timeseries.update({"Wind Generation":self.hopp_results["hybrid_plant"].wind.generation_profile})
            original_gen = original_gen + np.array(self.hopp_results["hybrid_plant"].wind.generation_profile)
            
        if "pv" in self.renewable_plant_design_type:
            
            self.timeseries.update({"PV Generation":self.hopp_results["hybrid_plant"].pv.generation_profile})
            original_gen = original_gen + np.array(self.hopp_results["hybrid_plant"].pv.generation_profile)
        if "battery" in self.renewable_plant_design_type:
            power_scale = 1 #kW
            self.timeseries.update({"Original Generation [kW]":original_gen})
            self.timeseries.update({"Optimized Dispatch [kW]":np.array(self.hopp_results["hybrid_plant"].grid.generation_profile)[:len(h2_hourly)]})
            # gen = [p * power_scale for p in list(self.hopp_results["hybrid_plant"].grid.generation_profile)]
            
        if "hydrogen_storage_soc" in self.h2_storage_results:
            # soc = self.h2_storage_results.pop("hydrogen_storage_soc")
            # self.timeseries.update({"H2 Storage SOC [kg]":soc})
            self.h2_storage_results.pop("hydrogen_storage_soc")
        # print(self.renewable_plant_design_type)
        # print(list(self.timeseries.keys()))
        self.hopp_results = {} #remove big data

        if isinstance(self.h2_transport_pipe_results,pd.DataFrame):
            self.h2_transport_pipe_results = self.h2_transport_pipe_results.T.to_dict()[0]
            

        if self.h2_storage_results is not None:
            new_keys = [k.replace("hydrogen","h2").replace("h2_storage","storage").replace("storage","h2_storage") for k in list(self.h2_storage_results.keys())]
            new_keys = [k.replace("h2_storage_","h2_storage: ") for k in new_keys]
            self.h2_storage_results = dict(zip(new_keys,list(self.h2_storage_results.values())))

        
        # if self.h2_transport_compressor_results is not None:
        #     all(k[0]==0 for k in df_sum.loc["Physics"].iloc[1]["h2_transport_pipe_results"].values())


    def update_re_plant_type(self,re_plant_type:str):
        self.re_plant_type = re_plant_type

    def update_h2_design_scenario(self,h2_storage_type:str,h2_transport_type:str):
        self.h2_storage_type = h2_storage_type
        self.h2_transport_type = h2_transport_type
        self.update_h2_design()
        # print(h2_storage_type)
        # new_keys = [k.replace("hydrogen","h2").replace("h2_storage","storage").replace("storage","h2_storage") for k in list(self.h2_storage_results.keys())]
        # dict(zip(new_keys,list(self.h2_storage_results.values())))

        # self.h2_storage_results[self.h2_storage_type] = 
    
    def get_physics_summary(self):
        #TODO: update this
        d = self.as_dict()
        summary = {k:v for k,v in d.items() if k!="hopp_results"}
        summary = {k:v for k,v in summary.items() if k!="electrolyzer_physics_results"}
        summary = {k:v for k,v in summary.items() if k!="timeseries"}
        #Below was just added
        summary = {k:v for k,v in summary.items() if k!="h2_storage_results"}
        summary = {k:v for k,v in summary.items() if k!="h2_transport_pipe_results"}
        summary = {k:v for k,v in summary.items() if k!="h2_transport_compressor_results"}

        if "cavern" in self.h2_storage_type:
            summary["h2_storage_type"] = "geologic"
        if "pipe" in self.h2_storage_type or "none" in self.h2_storage_type:
            summary["h2_storage_type"] = "on-site"

        return summary

    def get_physics_timeseries(self, save_wind_solar_timeseries = True):
        d = self.as_dict()
        ts_keys = ["timeseries","renewable_plant_design_type","re_plant_type","h2_storage_type","h2_transport_type"]
        summary = {k:v for k,v in d.items() if k in ts_keys}
        if not save_wind_solar_timeseries:
            if "wind" in self.renewable_plant_design_type:
                summary["timeseries"].pop("Wind Generation")
            if "pv" in self.renewable_plant_design_type:
                summary["timeseries"].pop("PV Generation")
        return summary

    def update_h2_design(self):
        key_desc = "{}: {}".format(self.h2_storage_type,self.h2_transport_type)
        self.h2_design_results[key_desc] = {}
        self.h2_design_results[key_desc].update(self.h2_storage_results)
        pipe_summary = {"h2_pipeline: {}".format(k):v for k,v in self.h2_transport_pipe_results.items()}
        compressor_summary = {"transport_compressor: {}".format(k.replace("compressor_","")):v for k,v in self.h2_transport_compressor_results.items()}
        self.h2_design_results[key_desc].update(pipe_summary)
        self.h2_design_results[key_desc].update(compressor_summary)
    
    def add_h2_design(self,h2_storage_type,h2_transport_type,h2_storage_results,h2_transport_pipe_results,h2_transport_compressor_results):
        key_desc = "{}: {}".format(h2_storage_type,h2_transport_type)
        if key_desc not in self.h2_design_results.keys():

            if isinstance(h2_transport_pipe_results,pd.DataFrame):
                h2_transport_pipe_results = h2_transport_pipe_results.T.to_dict()[0]

            if "hydrogen_storage_soc" in h2_storage_results:
                h2_storage_results.pop("hydrogen_storage_soc")
            new_keys = [k.replace("hydrogen","h2").replace("h2_storage","storage").replace("storage","h2_storage") for k in list(h2_storage_results.keys())]
            new_keys = [k.replace("h2_storage_","h2_storage: ") for k in new_keys]
            h2_storage_results = dict(zip(new_keys,list(h2_storage_results.values())))
            
            self.h2_design_results[key_desc] = {}
            self.h2_design_results[key_desc].update(h2_storage_results)
            pipe_summary = {"h2_pipeline: {}".format(k):v for k,v in h2_transport_pipe_results.items()}
            compressor_summary = {"transport_compressor: {}".format(k.replace("compressor_","")):v for k,v in h2_transport_compressor_results.items()}
            self.h2_design_results[key_desc].update(pipe_summary)
            self.h2_design_results[key_desc].update(compressor_summary)



@define
class NedOutputs(BaseClassNed):
    site: Site
    sweep_name: str = field(validator=contains(['offgrid-baseline','gridonly-baseline','offgrid-optimized']))
    # renewable_plant_design_type: str = field(validator=contains(['wind','wind-pv','wind-battery','wind-pv-battery','pv','pv-battery']))
    atb_year: int = field(validator=range_val(2020.,2050.))

    subsweep_name: Optional[str] = field(default = None) #"oversized,undersized,equal-sized"
    extra_desc: Optional[str] = field(default = "")
    
    save_data_info: dict = field(default = {})
    LCOH_Res: List[LCOHResults] = field(init = False)
    LCOE_Res: List[LCOEResults] = field(init = False)
    Finance_Res: List[FinanceResults] = field(init = False)
    Physics_Res: List[PhysicsResults] = field(init = False)
    
    save_summary_results: Optional[bool] = field(default = True)
    save_summary_separately: Optional[bool] = field(default = False)

    save_detailed_results: Optional[bool] = field(default = True)
    save_detailed_separately: Optional[bool] = field(default = False)
    save_some_detailed_results: Optional[bool] = field(default = False)

    save_detailed_LCOH: Optional[bool] = field(default = False)
    save_detailed_LCOE: Optional[bool] = field(default = False)
    save_timeseries: Optional[bool] = field(default = True)

    save_lcoe_cost_breakdown: Optional[bool] = field(default = False)
    save_lcoh_cost_breakdown: Optional[bool] = field(default = False)
    # saved_num: int = field(init = False)
    
    
    def __attrs_post_init__(self):
        

        self.LCOH_Res = []
        self.LCOE_Res = []
        self.Finance_Res = []
        self.Physics_Res = []
        if "summary_results" in self.save_data_info:
            self.save_summary_results = self.save_data_info["save_summary_results"]["flag"]
            self.save_summary_separately = self.save_data_info["save_summary_results"]["save_separately"]
        if "save_detailed_results" in self.save_data_info:
            self.save_detailed_results = self.save_data_info["save_detailed_results"]["flag"]
            self.save_detailed_separately = self.save_data_info["save_detailed_results"]["save_separately"]
            if "save_lcoe_cost_breakdown" in self.save_data_info["save_detailed_results"]:
                self.save_lcoe_cost_breakdown = self.save_data_info["save_detailed_results"]["save_lcoe_cost_breakdown"]
            if "save_lcoh_cost_breakdown" in self.save_data_info["save_detailed_results"]:
                self.save_lcoh_cost_breakdown = self.save_data_info["save_detailed_results"]["save_lcoh_cost_breakdown"]
            if not self.save_detailed_results:
                if "save_some_detailed_results" in self.save_data_info:
                    if self.save_data_info["save_some_detailed_results"]["flag"] and not self.save_detailed_results:
                        self.save_detailed_LCOH = self.save_data_info["save_some_detailed_results"]["save_LCOH"]
                        self.save_detailed_LCOE = self.save_data_info["save_some_detailed_results"]["save_LCOE"]
                        self.save_timeseries = self.save_data_info["save_some_detailed_results"]["save_timeseries"]


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
    
    def make_LCOH_detailed_results(self):
        temp = [pd.Series(self.LCOH_Res[i].get_lcoh_detailed_results(save_cost_breakdown=self.save_lcoh_cost_breakdown)) for i in range(len(self.LCOH_Res))]
        return pd.DataFrame(temp)

    def make_LCOE_detailed_results(self):
        temp = [pd.Series(self.LCOE_Res[i].get_lcoe_detailed_results(save_cost_breakdown=self.save_lcoe_cost_breakdown)) for i in range(len(self.LCOE_Res))]
        return pd.DataFrame(temp)
    
    def make_Physics_detailed_results(self, save_wind_solar_generation):
        temp = [pd.Series(self.Physics_Res[i].get_physics_timeseries(save_wind_solar_timeseries=save_wind_solar_generation)) for i in range(len(self.Physics_Res))]
        return pd.DataFrame(temp)

    def write_output_summary(self,output_dir:str):
        # self.saved_num +=1
        # output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}-{}_{}".format(self.site.id,self.site.latitude,self.site.longitude,self.site.state,self.site.county,self.extra_desc))
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}-{}-{}".format(self.site.id,self.site.latitude,self.site.longitude,self.site.state.replace(" ",""),self.atb_year,self.extra_desc))
        site_res = pd.Series(self.site.as_dict())
        lcoh_res = self.make_LCOH_summary_results()
        lcoe_res = self.make_LCOE_summary_results()
        phys_res = self.make_Physics_summary_results()
        fin_res = self.make_Finance_summary_results()

        if self.save_summary_separately:
            site_res.to_pickle(output_filepath_root + "--Site_Info.pkl")
            lcoh_res.to_pickle(output_filepath_root + "--LCOH_Summary.pkl")
            lcoe_res.to_pickle(output_filepath_root + "--LCOE_Summary.pkl")
            phys_res.to_pickle(output_filepath_root + "--Physics_Summary.pkl")
            fin_res.to_pickle(output_filepath_root + "--Financial_Summary.pkl")
        else:
            res = {"Site":site_res,"LCOH":lcoh_res,"LCOE":lcoe_res,"Physics":phys_res,"Financials":fin_res}
            pd.Series(res).to_pickle(output_filepath_root + "--Summary.pkl")
    
    def write_detailed_outputs(self,output_dir:str,save_wind_solar_generation):
        
        output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}-{}-{}".format(self.site.id,self.site.latitude,self.site.longitude,self.site.state.replace(" ",""),self.atb_year,self.extra_desc))
        site_res = pd.Series(self.site.as_dict())
        lcoh_res = self.make_LCOH_detailed_results()
        lcoe_res = self.make_LCOE_detailed_results()
        phys_res = self.make_Physics_detailed_results(save_wind_solar_generation)
        

        if self.save_detailed_separately:
            # site_res.to_pickle(output_filepath_root + "--Site_Info.pkl")
            lcoh_res.to_pickle(output_filepath_root + "--LCOH_Detailed.pkl")
            lcoe_res.to_pickle(output_filepath_root + "--LCOE_Detailed.pkl")
            phys_res.to_pickle(output_filepath_root + "--Physics_Timeseries.pkl")
            # fin_res.to_pickle(output_filepath_root + "--Financial_Summary.pkl")
        else:
            res = {"Site":site_res,"LCOH":lcoh_res,"LCOE":lcoe_res,"Physics":phys_res}
            pd.Series(res).to_pickle(output_filepath_root + "--Detailed.pkl")

    def write_outputs(self,output_dir,save_wind_solar_generation = True):
        

        if self.save_summary_results:
            self.write_output_summary(output_dir)
        if self.save_detailed_results:
            self.write_detailed_outputs(output_dir, save_wind_solar_generation)
        elif self.save_some_detailed_results:
            output_filepath_root = os.path.join(output_dir,"{}-{}_{}-{}-{}-{}".format(self.site.id,self.site.latitude,self.site.longitude,self.site.state.replace(" ",""),self.atb_year,self.extra_desc))
            if self.save_detailed_LCOE:
                lcoe_res = self.make_LCOE_detailed_results()
                lcoe_res.to_pickle(output_filepath_root + "--LCOE_Detailed.pkl")
            if self.save_detailed_LCOH:
                lcoh_res = self.make_LCOH_detailed_results()
                lcoh_res.to_pickle(output_filepath_root + "--LCOH_Detailed.pkl")
            if self.save_timeseries:
                phys_res = self.make_Physics_detailed_results(save_wind_solar_generation)
                phys_res.to_pickle(output_filepath_root + "--Physics_Timeseries.pkl")


        