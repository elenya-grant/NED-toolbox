import numpy as np

def weight_financial_parameters_vre_h2(capex_breakdown:dict,financial_assumptions:dict,pf_config:dict):
    vre_components = ["wind","solar","battery"]
    capex_vre = 0
    for vre_comp in vre_components:
        if vre_comp in capex_breakdown:
            capex_vre += capex_breakdown[vre_comp]
    
    h2_capex_items = [v for k,v in capex_breakdown.items() if "h2" in k]
    
    capex_h2 = capex_breakdown["electrolyzer"] + sum(h2_capex_items)
    # capex_h2 =  capex_electrolyzer_overnight + capex_desal + capex_compressor_installed + capex_storage_installed
    if "desal" in capex_breakdown:
        capex_h2 += capex_breakdown["desal"]
    fraction_capex_vre = capex_vre/(capex_vre + capex_h2)
    fraction_debt_financing_vre = 1/(1+1/financial_assumptions['vre_finance']['debt equity ratio of initial financing'])
    fraction_debt_financing_h2 = 1/(1+1/financial_assumptions['h2_finance']['debt equity ratio of initial financing'])
    fraction_equity_financing_vre = 1 - fraction_debt_financing_vre
    fraction_equity_financing_h2 = 1 - fraction_debt_financing_h2

    real_roe_vre = financial_assumptions['vre_finance']['leverage after tax nominal discount rate']
    real_roe_h2 = financial_assumptions['h2_finance']['leverage after tax nominal discount rate']

    real_interest_vre = financial_assumptions['vre_finance']['debt interest rate']
    real_interest_h2 = financial_assumptions['h2_finance']['debt interest rate']

    real_roe_combined = (fraction_equity_financing_vre*fraction_capex_vre*real_roe_vre + fraction_equity_financing_h2*(1-fraction_capex_vre)*real_roe_h2)\
                        /(fraction_equity_financing_vre*fraction_capex_vre + fraction_equity_financing_h2*(1-fraction_capex_vre))

    real_interest_combined = (real_interest_vre*fraction_capex_vre*fraction_debt_financing_vre + real_interest_h2*(1-fraction_capex_vre)*fraction_debt_financing_h2)\
                                /(fraction_capex_vre*fraction_debt_financing_vre + (1-fraction_capex_vre)*fraction_debt_financing_h2)

    debt_equity_ratio_combined = financial_assumptions['vre_finance']['debt equity ratio of initial financing']*fraction_capex_vre + financial_assumptions['h2_finance']['debt equity ratio of initial financing']*(1-fraction_capex_vre)

    if financial_assumptions['vre_finance']['total income tax rate'] != financial_assumptions['h2_finance']['total income tax rate']:

        total_income_tax_rate_combined = financial_assumptions['vre_finance']['total income tax rate']*fraction_capex_vre + financial_assumptions['h2_finance']['total income tax rate']*(1-fraction_capex_vre)
    else:
        total_income_tax_rate_combined = financial_assumptions['vre_finance']['total income tax rate']
    
    if financial_assumptions['vre_finance']['capital gains tax rate'] != financial_assumptions['h2_finance']['capital gains tax rate']:
        capitalgains_tax_rate_combined = financial_assumptions['vre_finance']['capital gains tax rate']*fraction_capex_vre + financial_assumptions['h2_finance']['capital gains tax rate']*(1-fraction_capex_vre)
    else:
        capitalgains_tax_rate_combined = financial_assumptions['vre_finance']['capital gains tax rate']
    gen_inflation = 0.00

    nominal_roe_combined = (real_roe_combined+1)*(1+gen_inflation)-1
    nominal_interest_combined = (real_interest_combined+1)*(1+gen_inflation)-1

    pf_config['params'].update({'debt interest rate':nominal_interest_combined})
    pf_config['params'].update({'leverage after tax nominal discount rate':nominal_roe_combined})
    pf_config['params'].update({'debt equity ratio of initial financing':debt_equity_ratio_combined})
    pf_config['params'].update({'total income tax rate':total_income_tax_rate_combined})
    pf_config['params'].update({'capital gains tax rate':capitalgains_tax_rate_combined})
    return pf_config