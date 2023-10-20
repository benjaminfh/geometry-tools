import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import MultiPolygon
import utils as utils
import json

DOOR_WIDTH = 0.9  # meters
min_pinch_size = 2.5  # meters

pickle_path = "data/planify/planify_finale.pickle"
# save_path = "data/planify/data_raw/{version_name}/".format(version_name=version_name)
# os.mkdir(save_path)

try:
    with open(pickle_path, "rb") as file:
        data = pd.read_pickle(file)
except Exception as e:
    print(f"Error: {e}")
    # print(f"Type of 'placement': {type(placement)}")

file_names = [
    "4c34f2d88c15307218ac3d2885338f61.jpg",
    "fac9afc096dcb56b8731e9b6b582bdda.jpeg",
    "72484edaa75e2566c50c7a8134ad0e54.jpg",
    "c4e2334eedaf64fee8a74228d5b9c4c3.jpeg",
    "d168f79355efd85e149682a1d270a817.jpg",
    "7bbf71f54a75bf983fd2b811d474cb11.jpg",
    "fa1e6e61ce9dc3e05ee85017102a8509.jpeg",
    "0e9dae2a99a4c7330359ff71611a6b01.jpeg",
]

row = data[data["img_name"] == file_names[0]]

# print(row)

# interested in the general column - we want to come up with a way to split the living room into different sections
living_room = row["general"].iloc[0]
doors = row["door"].iloc[0]
# print(living_room)
print(len(living_room.geoms))

# calc the scaling factor
scaling_factor = utils.est_scaling_factor(doors, DOOR_WIDTH)
print(f"Scaling factor: {scaling_factor}")

# create the figure and axes
fig = plt.figure(100, figsize=(12, 8))  # good size on 14" macbook pro
ax = fig.add_subplot(111)
ax.set_aspect("equal", "datalim")
# # hide the axes, ticks and box
# ax.axis("off")

# # create a polygon that is (door x door) / scaling_factor and plot it
# door_polygon = Polygon(
#     [
#         (0, 0),
#         (0, DOOR_WIDTH / scaling_factor),
#         (DOOR_WIDTH / scaling_factor, DOOR_WIDTH / scaling_factor),
#         (DOOR_WIDTH / scaling_factor, 0),
#     ]
# )

# # translate the door polygon to the centroid of the living room
# door_polygon = translate(
#     door_polygon,
#     living_room.centroid.x - door_polygon.centroid.x,
#     living_room.centroid.y - door_polygon.centroid.y,
# )

# # plot the door polygon
# x_door, y_door = door_polygon.exterior.xy
# ax.plot(x_door, y_door, alpha=0.8, color="black", linewidth=0.3)


for j, geom in enumerate(living_room.geoms):
    xs, ys = geom.exterior.xy
    # type = feature_cols[feature_type]["type"]

    # first plot the room/feature polygon area
    ax.fill(
        xs,
        ys,
        alpha=0.3,
        fc="b",
        ec="none",
    )
    # and plot the polygon outline
    ax.plot(xs, ys, alpha=0.8, color="black", linewidth=0.3)

print(f"Living room: {living_room}")

living_room = MultiPolygon([geom.buffer(0) for geom in living_room.geoms])

sub_rooms = utils.recursive_room_subdivision(living_room, scaling_factor, min_pinch_size, no_parents=False, plot=True, fig=fig, ax=ax)

print(f"subdivision results: {json.dumps(sub_rooms, default=lambda o: '<not serializable>')}")

sub_rooms = [subroom for subroom in sub_rooms if len(subroom["children"]) == 0]

print(f"subdivision results: {json.dumps(sub_rooms, default=lambda o: '<not serializable>')}")

multipoly = MultiPolygon([room["geom"].geoms[0] for room in sub_rooms])

print(multipoly)

fig99 = plt.figure(99, figsize=(12, 8))  # good size on 14" macbook pro
ax99 = fig99.add_subplot(111)
ax99.set_aspect("equal", "datalim")

for j, sub_room in enumerate(sub_rooms):
    geom = sub_room["geom"].geoms[0]
    xs, ys = geom.exterior.xy
    
    # first plot the room/feature polygon area
    ax99.fill(
        xs,
        ys,
        alpha=0.3,
        fc="b",
        ec="none",
    )
    # and plot the polygon outline
    ax99.plot(xs, ys, alpha=0.8, color="black", linewidth=0.3)
    # label the room with it's area
    ax99.text(
        geom.centroid.x,
        geom.centroid.y,
        "{:.2f}".format(geom.area),
        fontsize=8,
        horizontalalignment="center",
        verticalalignment="center",
    )


plt.show()
