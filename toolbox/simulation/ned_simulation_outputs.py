import numpy as np
from hopp.tools.utils import flatten_dict
def save_pf_config(pf,cost_run_desc,cost_type = "LCOH"):
    df = pf.cash_flow_out
    pf.vals
    pf.capital_items
    pf.feedstocks
    pf.fixed_costs
    pf.incentives
    pf.LCO
    pass
def calculate_hourly_correlation_coeff(wind_gen_kWh,solar_gen_kWh):
    num = sum((wind_gen_kWh[i]-np.mean(wind_gen_kWh))*(solar_gen_kWh[i]-np.mean(solar_gen_kWh)) for i in range(len(wind_gen_kWh)))
    x_d = sum(((wind_gen_kWh[i]-np.mean(wind_gen_kWh))**2) for i in range(len(wind_gen_kWh)))
    y_d = sum(((solar_gen_kWh[i]-np.mean(solar_gen_kWh))**2) for i in range(len(wind_gen_kWh)))
    r = num/((x_d*y_d)**0.5)
    return r

def summarize_renewables_info(hopp_results):
    hybrid_simulation = hopp_results["hybrid_plant"]
    summary = {}
    # timeseries_summary = {}
    plant_name = ""
    if "pv" in hybrid_simulation.technologies.keys():
        plant_name = "pv"
        system_model = hybrid_simulation.pv._system_model
        pv_energy_kWh_ac = np.array(system_model.Outputs.ac)/1e3 #AC inverter output power [W]
        pv_energy_kWh_dc = np.array(system_model.Outputs.dc)/1e3
        pv_info={"AEP [MWh-DC/year]":np.sum(np.array(system_model.Outputs.dc))/1e6,
        "AEP [MWh-AC/year]":np.sum(pv_energy_kWh_ac)/1e3,
        "Avg GHI":np.mean(system_model.Outputs.gh),
        "Capacity Factor [AC]":system_model.Outputs.capacity_factor_ac/100,
        "Capacity Factor [DC]":system_model.Outputs.capacity_factor/100, #hybrid_simulation.technologies["pv"].capacity_factor_dc
        "System Capacity [kW-AC]":system_model.SystemDesign.system_capacity/system_model.SystemDesign.dc_ac_ratio,
        "System Capacity [kW-DC]":system_model.SystemDesign.system_capacity,
        "Tilt Angle (deg)":system_model.SystemDesign.tilt,
        "Inverter Efficiency [%]":system_model.SystemDesign.inv_eff,
        "DC/AC ratio":system_model.SystemDesign.dc_ac_ratio,
        "Avg GHI":np.mean(system_model.Outputs.gh),
        "# Hours Sun-up":sum(system_model.Outputs.sunup),
        # "Something": system_model.Outputs.solrad_annual,
        "Mean Generation [kW-ac]":np.mean(pv_energy_kWh_ac),
        "Mean Generation [kW-dc]":np.mean(pv_energy_kWh_dc),
        "Generation Std [kW-ac]":np.std(pv_energy_kWh_ac),
        "Generation Std [kW-dc]":np.std(pv_energy_kWh_dc),
        "Footprint Area [m^2]":hybrid_simulation.technologies["pv"].footprint_area,
        "Land Coverage Area [m^2]":hybrid_simulation.technologies["pv"].land_coverage_area,
        }

        pv_summary = {"PV: {}".format(k):v for k,v in pv_info.items()}
        summary.update(pv_summary)
        # summary.update({"PV":pv_summary})
        # timeseries_summary.update({"PV Generation [kW-ac]":energy_kWh_ac})
        
    if "wind" in hybrid_simulation.technologies.keys():
        plant_name = "wind"
        if hybrid_simulation.wind.config.model_name == "floris":
            wind_energy_kWh_ac = np.array(hybrid_simulation.wind._system_model.gen) #floris
            # hybrid_simulation.wind._system_model.wind_resource_data
            # hybrid_simulation.wind._system_model.wind_resource_data['data']
            wind_info={
                "AEP [MWh/year]":hybrid_simulation.wind._system_model.annual_energy/1e3,
                "Avg Wind Speed": np.mean(hybrid_simulation.wind._system_model.speeds),
                "Avg Wind Direction":np.mean(hybrid_simulation.wind._system_model.wind_dirs),
                "Capacity Factor":hybrid_simulation.wind._system_model.capacity_factor,
                "System Capacity [kW]":hybrid_simulation.wind._system_model.system_capacity,
                "Number of Turbines":hybrid_simulation.wind._system_model.nTurbs,
                "Mean Generation [kW]":np.mean(wind_energy_kWh_ac),
                "Generation Std [kW]":np.std(wind_energy_kWh_ac),
                "Operational Losses [%]":hybrid_simulation.wind._system_model._operational_losses,
            }

        else:
        
            system_model = hybrid_simulation.wind._system_model
            wind_energy_kWh_ac = np.array(hybrid_simulation.wind._system_model.Outputs.gen)
            wind_info={"AEP [MWh/year]":system_model.Outputs.annual_energy/1e3,
            "Avg Wind Speed":system_model.Outputs.wind_speed_average,
            "Avg Wind Direction":system_model.Outputs.wind_speed_average, #TODO: finish this
            "Capacity Factor":system_model.Outputs.capacity_factor/100,
            "System Capacity [kW]":system_model.Farm.system_capacity,
            "Number of Turbines":system_model.num_turbines,
            "Mean Generation [kW]":np.mean(wind_energy_kWh_ac),
            "Generation Std [kW]":np.std(wind_energy_kWh_ac),
            }

        wind_summary = {"Wind: {}".format(k):v for k,v in wind_info.items()}
        # summary.update({"Wind":wind_summary})
        summary.update(wind_summary)
    if ("wind" in hybrid_simulation.technologies.keys()) and ("pv" in hybrid_simulation.technologies.keys()):
        plant_name = "wind-pv"
        correlation_pvac = calculate_hourly_correlation_coeff(wind_energy_kWh_ac,pv_energy_kWh_ac)
        correlation_pvdc = calculate_hourly_correlation_coeff(wind_energy_kWh_ac,pv_energy_kWh_dc)
        std_pvac = np.std(wind_energy_kWh_ac + pv_energy_kWh_ac)
        std_pvdc = np.std(wind_energy_kWh_ac + pv_energy_kWh_dc)
        wind_solar_info = {
            "Hourly Correlation Coefficient [PVAC]":correlation_pvac,
            "Hourly Correlation Coefficient [PVDC]":correlation_pvdc,
            "Generation Std [kW-PVDC]":std_pvdc,
            "Generation Std [kW-PVAC]":std_pvac,
        }

        wind_solar_summary = {"Wind & Solar: {}".format(k):v for k,v in wind_solar_info.items()}
        summary.update(wind_solar_summary)
        # summary.update({"Wind & Solar":wind_solar})
        # timeseries_summary.update({"Wind Generation [kW-ac]":energy_kWh_ac})
    # hybrid_simulation.grid._system_model #Load, GridLimits, Outputs
    if "battery" in hybrid_simulation.technologies.keys():
        plant_name +="-battery"
        battery = {"System Capacity [kW]":hybrid_simulation.technologies["battery"].system_capacity_kw,
        "System Capacity [kWh]":hybrid_simulation.technologies["battery"].system_capacity_kwh,
        "Footprint Area":hybrid_simulation.technologies["battery"].footprint_area,
        "Annual Energy [MWh/year]":hybrid_simulation.technologies["battery"].annual_energy_kwh/1e3}
        battery_summary = {"Battery: {}".format(k):v for k,v in battery.items()}
        summary.update(battery_summary)
        # summary.update({"Battery":battery})
    if plant_name=="":
        plant_name = "grid"
    grid_info = {"Hybrid Nominal Capacity":hybrid_simulation.grid.hybrid_nominal_capacity,
    "Interconnection Size [kW]":hybrid_simulation.grid.interconnect_kw,
    "Missed Load":sum(hybrid_simulation.grid.missed_load),
    "Annual Energy [MWh/year]":hybrid_simulation.grid.annual_energy_kwh/1e3,
    "System Capacity [kW]":hybrid_simulation.grid.system_capacity_kw}
    grid = {"Grid: {}".format(k):v for k,v in grid_info.items()}
    summary.update(grid)
    # summary.update({"Grid":grid})

    # timeseries_summary.update({"Renewable Generation Only [kW]":renewables_generation})
    
    # timeseries_summary.update({"Energy to Electrolyzer [kW]":np.array(hybrid_simulation.grid._system_model.Outputs.system_pre_interconnect_kwac[0:8760])})
    # hybrid_simulation.grid._system_model.Outputs.system_pre_curtailment_kwac
    # hybrid_simulation.grid._system_model.Outputs.system_pre_interconnect_kwac
    # hybrid_simulation.grid.generation_profile_wo_battery = total_gen_before_battery
    return summary, plant_name