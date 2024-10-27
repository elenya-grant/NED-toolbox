from scipy.optimize import minimize,Bounds,OptimizeResult #,milp,NonlinearConstraint
import numpy as np
import scipy
from hopp.type_dec import FromDictMixin
from attrs import define, field
from typing import List, Sequence, Optional, Union
from toolbox.simulation.run_single_case import run_simple_single_simulation
from toolbox.utilities.ned_logger import opt_logger as opt_log
from toolbox.simulation.plant.design.base_optimization import SimulationResults, OptimizationResults, RenewableGenerationTracker
import toolbox.simulation.plant.design.optimization_tools as opt_tools


def objective_func(x,ned_man,ned_out,config,hopp_site,include_battery,col_order,re_plant_desc,OptRes,merit_figure):
    if len(x) == 2:
        wind_capacity_mw,pv_capacity_mwdc = x
    else:
        if "wind" in re_plant_desc:
            wind_capacity_mw = x[0]
            pv_capacity_mwdc = 0.0
        if "pv" in re_plant_desc:
            pv_capacity_mwdc = x[0]
            wind_capacity_mw = 0.0
    # print(x)
    pv_capacity_mwac = pv_capacity_mwdc/ned_man.dc_ac_ratio
    # if not include_battery:
    #     # without battery can use the saving generation thing
    #     hopp_results,REgen = opt_tools.make_hopp_results_for_saved_generation(wind_capacity_mw,pv_capacity_mwdc,hopp_site,ned_man,config,REgen)
    #     lcoh,wind_size_mw,pv_size_mwdc, h2_storage_capac = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=5,hopp_results=hopp_results)
    # else:
    lcoh,wind_size_mw,pv_size_mwdc, h2_storage_capac, elec_cf = run_simple_single_simulation(ned_man,ned_out,config,hopp_site,wind_capacity_mw,pv_capacity_mwac,include_battery,output_level=5)

    # opt_log.info("wind: {} MW ---- pv: {}MWdc ---- LCOH ${}/kg".format(wind_capacity_mw,pv_capacity_mwdc,lcoh))
    
    opt_sim_res = SimulationResults(
        atb_scenario = ned_man.baseline_atb_case,
        re_plant_type = re_plant_desc,
        h2_storage_type = ned_man.baseline_h2_storage_type,
        # optimization_desc=re_plant_desc,
        x_names = col_order,
        x_values_input = x,
        wind_size_mw_actual=wind_size_mw,
        pv_size_mwdc_actual=pv_size_mwdc,
        y_name = merit_figure,
        y_value = lcoh,
        h2_storage_capacity=h2_storage_capac,
        electrolyzer_cf=elec_cf)
    OptRes.add_simulation_results(opt_sim_res)
    return lcoh

# def optimize_design_milp(ned_site,ned_man,ned_out,config,hopp_site,re_plant_desc:str,OptRes:OptimizationResults,REgen:RenewableGenerationTracker):
#     #https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html
#     #https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html#scipy.optimize.linprog
#     init_simplex,col_order = ned_site.get_final_simplex_for_plant(re_plant_desc)
#     bnds = ned_site.get_bounds_for_plant_design(re_plant_desc)
#     if "battery" in re_plant_desc:
#         include_battery = True
#     else:
#         include_battery = False
#     if len(col_order)==1:
#         bnds = Bounds(lb = bnds[0],ub = bnds[1])

#     milp(c,integrality = 1, bounds = bnds, constraints = constraints)
# def optimize_design_brute_force(inputs):
#     #https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brute.html#scipy.optimize.brute
#     pass
# def optimize_design_linprog_simplex(inputs):
    
#     pass
# def optimize_design_slsqp(ned_site,ned_man,ned_out,config,hopp_site,re_plant_desc:str,OptRes:OptimizationResults,REgen:RenewableGenerationTracker):
#     integer_capacity_constraint_wind = lambda x: 6*int(x/6)
#     integer_capacity_constraint_pvdc = lambda x: 5*int(x/5)
#     NonlinearConstraint(integer_capacity_constraint_wind,finite_diff_rel_step=6)
#     pass

# def callback(intermediate_result: OptimizeResult):
#     x_init = intermediate_result.get("x")
    
#     pass
# def optimize_design(ned_site,ned_man,ned_out,config,hopp_site,re_plant_desc:str,OptRes:OptimizationResults,extra_desc):
def optimize_design(ned_site,ned_man,ned_out,config,hopp_site,re_plant_desc:str,OptRes:OptimizationResults,merit_figure,h2_storage_type,atb_cost_scenario):
    # extra_desc = "{}-{}".format(merit_figure.replace("lcoh-",""),h2_storage_type)
    # init_simplex,col_order = ned_site.get_final_simplex_for_plant(re_plant_desc)
    ned_man.baseline_h2_storage_type = h2_storage_type
    ned_man.baseline_atb_case = atb_cost_scenario
    init_simplex,col_order = ned_site.get_final_simplex_for_hybrid_plant(re_plant_desc,merit_figure,atb_cost_scenario)
    # bnds = (wind_bounds,solar_bounds)
    opt_log.info("RE Plant: {}".format(re_plant_desc))
    # bnds = ned_site.get_bounds_for_plant_design(re_plant_desc)
    bnds = ned_site.get_bounds_for_plant_design(re_plant_desc)
    if "battery" in re_plant_desc:
        include_battery = True
    else:
        include_battery = False
    if len(col_order)==1:
        bnds = Bounds(lb = bnds[0],ub = bnds[1])
    methd = "Nelder-Mead"
    opts = {"maxiter":20,"disp":False}
    opts.update({"xatol":6,"fatol":0.1,"adaptive":True})
    ntol = None
    opts.update({"initial_simplex":init_simplex})
    x0 = init_simplex[0]
    res = minimize(objective_func,x0,args=(ned_man,ned_out,config,hopp_site,include_battery,col_order,re_plant_desc,OptRes,merit_figure),method = methd,bounds = bnds,tol=ntol,options=opts)
    return res


