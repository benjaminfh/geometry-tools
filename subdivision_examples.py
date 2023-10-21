import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import MultiPolygon
import utils as utils
import traceback



DOOR_WIDTH = 0.9  # meters
MIN_PINCH_SIZE = 2.5  # meters
TEST_IDX = 6

sample_file_names = [
    "fac9afc096dcb56b8731e9b6b582bdda.jpeg",  # simple case
    "72484edaa75e2566c50c7a8134ad0e54.jpg",  # case that requires iteration on MIN_PINCH_SIZE - try 2.5
    "c4e2334eedaf64fee8a74228d5b9c4c3.jpeg",  # case that buffering method fails on – pinch ratio is too small
    "d168f79355efd85e149682a1d270a817.jpg",  # 
    "7bbf71f54a75bf983fd2b811d474cb11.jpg",  # complex case - works reasonably well
    "fa1e6e61ce9dc3e05ee85017102a8509.jpeg", # simple case
    "0e9dae2a99a4c7330359ff71611a6b01.jpeg", # moderately complex case
    "4c34f2d88c15307218ac3d2885338f61.jpg",  # simultaneously finds 2 pinches (2 split points) which we don't handle yet
]

pickle_path = "sample_data/sample.pickle"


if __name__ == "__main__":

    try:
        with open(pickle_path, "rb") as file:
            data = pd.read_pickle(file)
    except Exception as e:
        print(traceback.format_exc())

    test_row = data[data["img_name"] == sample_file_names[TEST_IDX]]
    general = test_row["general"].iloc[0]
    doors = test_row["door"].iloc[0]

    # estimate the scaling factor from the door width -- usually doors are about 0.9 meters wide
    scaling_factor = utils.est_scaling_factor(doors, DOOR_WIDTH)
    print(f"Scaling factor: {scaling_factor}")

    # Plot some shapes
    fig = plt.figure(1, figsize=(12, 8))
    ax = fig.add_subplot(111)
    ax.set_aspect("equal", "datalim")

    for j, geom in enumerate(general.geoms):
        xs, ys = geom.exterior.xy

        ax.fill(
            xs,
            ys,
            alpha=0.3,
            fc="b",
            ec="none",
        )

        ax.plot(xs, ys, alpha=0.8, color="black", linewidth=0.3)

    # buffer(0) as a way to fix invalid geometries
    general = MultiPolygon([geom.buffer(0) for geom in general.geoms])
    # search the general geometry for pinch points and subdivide
    sub_rooms, reason = utils.recursive_room_subdivision(general, scaling_factor, MIN_PINCH_SIZE, no_parents=True, plot=True, fig=fig, ax=ax)
    # create a MultiPolygon from the sub rooms
    multipoly = MultiPolygon([room["geom"].geoms[0] for room in sub_rooms])

    # Plot the sub rooms on a new figure
    fig2 = plt.figure(99, figsize=(12, 8)) 
    ax2 = fig2.add_subplot(111)
    ax2.set_aspect("equal", "datalim")

    for j, sub_room in enumerate(sub_rooms):
        geom = sub_room["geom"].geoms[0]
        xs, ys = geom.exterior.xy
        
        # first plot the room/feature polygon area
        ax2.fill(
            xs,
            ys,
            alpha=0.3,
            fc="b",
            ec="none",
        )
        # and plot the polygon outline
        ax2.plot(xs, ys, alpha=0.8, color="black", linewidth=0.3)
        # label the room with it's area
        ax2.text(
            geom.centroid.x,
            geom.centroid.y,
            "{:.2f}".format(geom.area),
            fontsize=8,
            horizontalalignment="center",
            verticalalignment="center",
        )

    plt.show()
