import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
def find_most_square_layout(n_turbs):
    n_turbs_per_row = np.floor_divide(n_turbs,np.sqrt(n_turbs))
    n_rows_min = n_turbs//n_turbs_per_row
    remainder_turbs = n_turbs%n_turbs_per_row
    if remainder_turbs>n_turbs_per_row:
        n_extra_rows = np.ceil(remainder_turbs/n_turbs_per_row)
    elif remainder_turbs==0:
        n_extra_rows = 0
    else:
        n_extra_rows = 1

    n_rows = n_rows_min + n_extra_rows

    return n_turbs_per_row,n_rows

def make_square_layout(n_turbs,rotor_diam,row_spacing,turbine_spacing):
    intrarow_spacing = turbine_spacing*rotor_diam #distance between turbines in same row
    interrow_spacing = row_spacing*n_turbs #distance between rows
    n_turbs_per_row,n_rows = find_most_square_layout(n_turbs)
    x_pos = intrarow_spacing*np.arange(0,int(n_turbs_per_row))
    y_pos = interrow_spacing*np.arange(0,int(n_rows))

    layout_x = np.repeat(x_pos,len(y_pos))
    layout_y = np.tile(y_pos,len(x_pos))

    return layout_x, layout_y


def make_site_boundaries_for_square_layout(n_turbs,rotor_diam,row_spacing,turbine_spacing):
    intrarow_spacing = turbine_spacing*rotor_diam #distance between turbines in same row
    interrow_spacing = row_spacing*rotor_diam #distance between rows
    
    n_turbs_per_row,n_rows = find_most_square_layout(n_turbs)
    center_x = ((n_turbs_per_row/2)*intrarow_spacing) #+ (intrarow_spacing*0.5)
    center_y = ((n_rows/2)*interrow_spacing) + (interrow_spacing*0.25)
    x_dist_m = 2*center_x
    y_dist_m = 2*center_y
    
    # x_pos = intrarow_spacing*np.arange(0,int(n_turbs_per_row))
    # y_pos = interrow_spacing*np.arange(0,int(n_rows))

    # x_dist_m = (n_turbs_per_row*intrarow_spacing) + (2*intrarow_spacing*buffer_mult_x)
    # y_dist_m = (n_rows*interrow_spacing) + (2*interrow_spacing*buffer_mult_y)
    p0 = [0.0,0.0]
    # p1 = [0.0,x_dist_m]
    # p2 = [y_dist_m,x_dist_m]
    # p3 = [y_dist_m,0.0]
    p1 = [0.0,y_dist_m]
    p2 = [x_dist_m,y_dist_m]
    p3 = [x_dist_m,0.0]
    verts = [p0,p1,p2,p3]
    return {"site_boundaries":{"verts":verts,"verts_simple":verts}}

# ---------------------------------------------
# print("nturbs needed: {}".format(n_turbs))

# print("wanted: {} by {}".format(n_turbs_per_row,n_rows))
# print("results: {} by {}".format(nturbs_x,nturbs_y))
# # print("nturbs x: {}".format(nturbs_x))
# # print("nturbs y: {}".format(nturbs_y))
# print("n turbs resulted: {}".format(len(layout_x)))


# x_pos = dist_between_turbs*np.arange(0,int(n_turbs_per_row))
# y_pos = dist_between_rows*np.arange(0,int(n_rows))

# fig,ax = plt.subplots(1,1)
# # for i in range(len(grid_lines)):
# #     ax.plot(*grid_lines[i].xy,c="green",ls="--",alpha=0.5,lw=1.0) 
# ax.scatter(layout_x,layout_y,c="blue")
# # ax.scatter(layout_x_,layout_y_,c="orange")
# ax.plot(*site_polygon.exterior.xy,c="red")
# ax.scatter(*site_polygon.centroid.xy,c="red")

# max_val = max([max(layout_x),max(layout_y),max(max(site_bound["verts"]))]) + 100
# # max(max(site_bound["verts"]))

# ax.set_xlim([-100,max_val])
# ax.set_ylim([-100,max_val])
# []