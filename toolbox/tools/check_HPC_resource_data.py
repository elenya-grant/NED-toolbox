# from hopp.simulation.technologies.resource.wind_toolkit_data import HPCWindData
from hopp.simulation.technologies.sites.site_info import SiteInfo


dx = 11.5*1e3
x0 = 0
y0 = 0
verts = [[x0,y0],[x0+dx,y0],[x0+dx,y0+dx],[x0,y0+dx]]
site_data = {
    "lat":35.2,
    "lon":-101.94,
    "year":2013,
    "site_boundaries":{
        "verts": verts,
        "verts_simple":verts,
    }}

def check_wind_toolkit():
    site_input = {
        "data":site_data,
        "renewable_resource_origin": "HPC",
        "solar_resource_file": "",
        "wind_resource_file":"",
        "hub_height": 115.0,
        "wind_resource_origin": "WTK",
        "wind": True,
        "solar": False,
        # "wtk_source_path":"/kfs2/",
        # "nsrdb_source_path":"/kfs2/",
    }

    site = SiteInfo.from_dict(site_input)
    return site

def check_nsrdb():
    site_input = {
        "data":site_data,
        "renewable_resource_origin": "HPC",
        "solar_resource_file": "",
        "wind_resource_file":"",
        "hub_height": 115.0,
        "wind_resource_origin": "WTK",
        "wind": False,
        "solar": True,
        # "wtk_source_path":"/kfs2/",
        # "nsrdb_source_path":"/kfs2/",
    }

    site = SiteInfo.from_dict(site_input)
    return site


if __name__ == "__main__":
    nsrdb_site = check_nsrdb()

    print("downloaded NSRDB Data")
    wtk_site = check_wind_toolkit()
    print("downloaded Wind Toolkit Data")