


def convert_pf_res_to_pf_config(pf_config):
    pf_config_new = {}
    config_keys = list(pf_config.keys())
    pf_config_new.update({"params":{}})
    
    new_params = {}
    params = pf_config['params']
    for i in params:
        new_params.update({i:params[i]})
    pf_config_new.update({"params":new_params})
    
    if 'feedstocks' in config_keys:
        feedstocks = {}
        feedstock_keys = ["name","usage","unit","cost","escalation"]
        variables = pf_config['feedstocks']
        for i in variables:
            vals = [i,variables[i].usage,variables[i].unit,variables[i].cost,variables[i].escalation]
            feedstocks.update({i:dict(zip(feedstock_keys,vals))})
        pf_config_new.update({"feedstocks":feedstocks})
    if 'capital_items' in config_keys:
        variables = pf_config['capital_items']
        capital_items = {}
        citem_keys = ["name","cost","depr_type","depr_period","refurb"]
        for i in variables:
            vals = [i,variables[i].cost,variables[i].depr_type,variables[i].depr_period,variables[i].refurb]
            capital_items.update({i:dict(zip(citem_keys,vals))})
        pf_config_new.update({"capital_items":capital_items})
    if 'fixed_costs' in config_keys:
        variables = pf_config['fixed_costs']
        fixed_costs = {}
        fitem_keys = ["name","usage","unit","cost","escalation"]
        for i in variables:
            vals = [i,variables[i].usage,variables[i].unit,variables[i].cost,variables[i].escalation]
            fixed_costs.update({i:dict(zip(fitem_keys,vals))})
        pf_config_new.update({"fixed_costs":fixed_costs})
    
    if 'incentives' in config_keys:
        variables = pf_config['incentives']
        incentive_keys = ["name","value","decay","sunset_years","tax_credit"]
        incentives = {}
        for i in variables:
            vals = [i,variables[i].value,variables[i].decay,variables[i].sunset_years,variables[i].tax_credit]
            incentives.update({i:dict(zip(incentive_keys,vals))})
    pf_config_new.update({"incentives":incentives})
    return pf_config_new