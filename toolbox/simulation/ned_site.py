from hopp.simulation.base import BaseClass
from toolbox.simulation.ned_base import BaseClassNed
from typing import Iterable, List, Sequence, Optional, Union, TYPE_CHECKING

import numpy as np
from hopp.type_dec import hopp_float_type
from hopp.utilities.validators import contains, range_val, gt_zero
from attrs import define, field
from hopp.simulation.technologies.pv.pv_plant import PVConfig
import copy
@define
class Site(BaseClassNed):
    latitude: hopp_float_type = field(converter = hopp_float_type)
    longitude: hopp_float_type = field(converter = hopp_float_type)
    # latitude: float = field(validator=gt_zero)
    # longitude: float = field(validator=gt_zero)
    
    distance_to_salt_cavern: float = field(converter = hopp_float_type)
    distance_to_rock_cavern: float = field(converter = hopp_float_type)
    # balancing_area_id: int = field(validator=range_val(1,134))

    balancing_area: Optional[str] = field(default = None)
    # resource_year: Optional[int] = field(default = None, validator=range_val(2007, 2013))

    state: Optional[str] = field(default=None)
    county: Optional[str] = field(default=None)
    CountyFP: Optional[float] = field(default=None)
    id: Optional[float] = field(default=None)

    rock_cavern_loc: Optional[str] = field(default=None)
    salt_cavern_loc: Optional[str] = field(default=None)
    feedstock_region: str = field(default="US Average", validator=contains(['East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central','US Average']))
    


@define 
class NedManager(BaseClassNed):
    output_directory: str = field()
    renewable_resource_origin: str = field()
    atb_year: int = field(validator=range_val(2020,2050))
    atb_cost_cases_hopp: dict
    atb_cost_cases_electrolyzer: dict
    atb_cases_desc: List[str]
    h2_system_types: dict
    profast_config: dict

    baseline_atb_case: str
    baseline_incentive_opt: int
    baseline_h2_storage_type: str

    
    re_plant_types: dict
    re_plant_capacity_multiplier: Optional[float] = field(default = None)
    optimize_design: Optional[bool] = field(default = False)
    electrolyzer_size_mw: float = field(default = 720)
    resource_year: Optional[int] = field(default = 2013, validator=range_val(2007, 2014))
    site_resolution_km: Optional[float] = field(default = 11.5)

    dc_ac_ratio: float = field(init=False)
    turbine_size_mw: float = field(init=False)
    rotor_diameter: float = field(init=False)
    hub_height: float = field(init=False)
    row_spacing_D: float = field(init=False)
    turbine_spacing_D: float = field(init=False)
    battery_size_mw: float = field(init=False)
    battery_size_mwh: float = field(init=False)

    wind_technologies_config_default: dict = field(init=False)
    pv_technologies_config_default: dict = field(init=False)
    battery_technologies_config_default: dict = field(init=False)
    def set_renewable_specs(self,init_config):
        self.__setattr__("turbine_size_mw",init_config.turbine_config["turbine_rating"])
        self.__setattr__("rotor_diameter",init_config.turbine_config["rotor_diameter"])
        self.__setattr__("hub_height",init_config.turbine_config["hub_height"])
        
        self.__setattr__("row_spacing_D",init_config.greenheart_config["site"]["wind_layout"]["row_spacing"])
        self.__setattr__("turbine_spacing_D",init_config.greenheart_config["site"]["wind_layout"]["turbine_spacing"])
        
        if "panel_system_design" in init_config.hopp_config["technologies"]["pv"]:
            if "SystemDesign" in init_config.hopp_config["technologies"]["pv"]["panel_system_design"]:
                dc_ac_ratio = init_config.hopp_config["technologies"]["pv"]["panel_system_design"]["SystemDesign"]["dc_ac_ratio"]
            else:
                dc_ac_ratio = init_config.hopp_config["technologies"]["pv"]["panel_system_design"]["dc_ac_ratio"]
        elif "dc_ac_ratio" in init_config.hopp_config["technologies"]["pv"]:
            dc_ac_ratio = init_config.hopp_config["technologies"]["pv"]["dc_ac_ratio"]
        else:
            dc_ac_ratio = PVConfig.get_model_defaults()["dc_ac_ratio"]
        
        self.__setattr__("dc_ac_ratio",dc_ac_ratio)

        self.__setattr__("battery_size_mw",init_config.hopp_config["technologies"]["battery"]["system_capacity_kw"]/1e3)
        self.__setattr__("battery_size_mwh",init_config.hopp_config["technologies"]["battery"]["system_capacity_kwh"]/1e3)
        
    def set_default_hopp_technologies(self,default_hopp_tech):
        self.__setattr__("battery_technologies_config_default",copy.deepcopy(default_hopp_tech["battery"]))
        pv_tech = copy.deepcopy(default_hopp_tech["pv"])
        pv_tech.pop("system_capacity_kw")
        if "tilt" in pv_tech:
            pv_tech.pop("tilt")
        
        self.__setattr__("pv_technologies_config_default",pv_tech)
        wind_tech = copy.deepcopy(default_hopp_tech["wind"])
        wind_tech.pop("num_turbines")
        self.__setattr__("wind_technologies_config_default",wind_tech)
       

