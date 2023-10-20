import numpy as np
from shapely.ops import triangulate, unary_union, nearest_points, split
from shapely.affinity import scale, translate, rotate
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, MultiPoint
import matplotlib.pyplot as plt
import traceback


def est_scaling_factor(multiPoly: MultiPolygon, typical_max_dim: float) -> float:
    geom_max_dim = []
    for geom in multiPoly.geoms:
        box = geom.minimum_rotated_rectangle
        x, y = box.exterior.coords.xy
        edge_lengths = (
            Point(x[0], y[0]).distance(Point(x[1], y[1])),
            Point(x[1], y[1]).distance(Point(x[2], y[2])),
        )
        geom_max_dim.append(max(edge_lengths))

    scaling_factor = typical_max_dim / np.median(geom_max_dim)
    return scaling_factor


def marching_buffer(
    poly: Polygon,
    steps: list,
    stop_before_intersection: bool = True,
    iteration:int=0,
    plot: bool=False,
    fig: plt.figure=None,
    ax: plt.axes=None,
) -> (MultiPolygon, float):
    def do_plot(buffer, plot, fig, ax):
        if plot:
            if fig is None:
                fig = plt.figure(110)
                ax = fig.add_subplot(111)
                ax.set_aspect("equal", "datalim")
            elif ax is None:
                ax = fig.add_subplot(111)
                ax.set_aspect("equal", "datalim")

            for geom in buffer.geoms:
                xsi, ysi = geom.exterior.xy
                ax.plot(
                    xsi,
                    ysi,
                    alpha=1,
                    color=colours[iteration % len(colours)],
                    linewidth=0.1,
                    linestyle="--",
                )
    
    buffer_list = []
    intersection = False
    colours = ["k", "r", "m"]
    for i, step in enumerate(steps):
        # try marching inwards with a buffer
        try:
            # step = step / scaling_factor  # establish the correct scale
            # buffer the polygon inwards by
            buffer = poly.buffer(-step)

            # if the buffer does not self-intersect, then we haven't found a pinch point yet
            # when we do, it'll return a multipolygon - this is our trigger
            if isinstance(buffer, Polygon):
                buffer = MultiPolygon([buffer])
            else:
                intersection = True

        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            print("aborting..")
            break

        if intersection:
            # print(f"Found an intersection at step {i+1}")
            try:
                step_size = steps[i] - steps[i - 1]
            except:
                print(
                    "Interescetion found at first step - reduce the step size and try again!"
                )
                return None, None

            if stop_before_intersection:
                # return the penultimate buffer polygon - before we found the intersection
                # print("Returning the previous (non-intersecting) buffer")
                return buffer_list[-1], step_size
            else:
                # otherwise, return the latest (intesecting) polygon
                # print("Returning the current (intersecting) buffer")
                do_plot(buffer, plot, fig, ax)
                return buffer, step_size
        
        # if no intersection, store and continue...
        do_plot(buffer, plot, fig, ax)
        buffer_list.append(buffer)
    # if we get here, we've run out of steps and not found an intersection
    # print("No intersection found in this polygon – returning None")
    return None, None


def process_buffer(
    buffer: MultiPolygon,
    parent_poly: Polygon,
    plot: bool=False,
    fig: plt.figure=None,
    ax: plt.axes=None,
) -> MultiPolygon:
    assert isinstance(buffer, MultiPolygon), "Intersection must be a MultiPolygon"
    assert len(buffer.geoms) == 2, f"Intersection must have exactly two geometries, found {len(buffer.geoms)}"

    if plot:
        if fig is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.set_aspect("equal", "datalim")
        elif ax is None:
            ax = fig.add_subplot(111)
            ax.set_aspect("equal", "datalim")

        for geom in buffer.geoms:
            xsi, ysi = geom.exterior.xy
            ax.plot(xsi, ysi, alpha=0.8, color="black", linewidth=0.3)

    # find the nearest points between the two polygons
    near_points = nearest_points(buffer.geoms[0], buffer.geoms[1])
    # create a line between the two points
    line_btw = LineString([near_points[0], near_points[1]])
    # rotate the line 90 degrees about its centre
    cutting_tool = rotate(line_btw, 90, origin=line_btw.centroid)
    # extend the line to the edge of the polygon
    cutting_tool = scale(cutting_tool, 10, 10, origin=cutting_tool.centroid)
    # find the points of intersection between the line and the livingroom exterior
    intersections = cutting_tool.intersection(parent_poly.geoms[0].exterior)
    # find the two intersection points which are closet to the line centroid
    inters_distances = [
        inters.distance(line_btw.centroid) for inters in intersections.geoms
    ]
    # map the distances to the points and then sort by distance asc; take the first two indices
    inters = [
        {"point": geom, "distance": inters_distances[i]}
        for i, geom in enumerate(intersections.geoms)
    ]
    inters_sorted = sorted(inters, key=lambda k: k["distance"])
    inters_sorted = [inter["point"] for inter in inters_sorted]

    # create a line between the two nearest intersection points - we only want to split at the local pinch point we found
    line_cutting = LineString([inters_sorted[0], inters_sorted[1]])
    # split the living room polygon into two polygons using the cutting line
    parent_poly_split = split(parent_poly.geoms[0], line_cutting)

    if plot:
        # plot the nearest points
        np_x = [near_points[0].x, near_points[1].x]
        np_y = [near_points[0].y, near_points[1].y]
        ax.scatter(np_x, np_y, marker="o", color="red")
        # plot the line between the nearest points
        line_x, line_y = line_btw.xy
        ax.plot(line_x, line_y, alpha=0.8, color="red", linewidth=0.5)
        # plot the cutting line
        line_x, line_y = cutting_tool.xy
        ax.plot(line_x, line_y, alpha=0.8, color="red", linewidth=0.5)
        # plot the cutting line intersection points
        xi = [inters.x for inters in intersections.geoms]
        yi = [inters.y for inters in intersections.geoms]
        ax.scatter(xi, yi, marker="o", color="green")
        # plot the closest two points
        x_closest = [inters.x for inters in inters_sorted[:2]]
        y_closest = [inters.y for inters in inters_sorted[:2]]
        ax.scatter(x_closest, y_closest, marker="o", color="purple")
        # plot the split living room - buffer it to make it more visible
        temp_scale = max(parent_poly_split.geoms[0].bounds) / 2
        parent_poly_split_plot = parent_poly_split.buffer(-temp_scale/200)
        for geom in parent_poly_split_plot.geoms:
            xs, ys = geom.exterior.xy
            ax.plot(xs, ys, alpha=0.8, color="red", linewidth=2)

    parent_poly_split = MultiPolygon([geom for geom in parent_poly_split.geoms if isinstance(geom, Polygon)])
    return parent_poly_split


def subdivide_room(room: MultiPolygon, min_pinch_size: float, scaling_factor: float, iterations:int=2, step_reduction_factor=10, plot:bool=False, fig=None, ax=None) -> MultiPolygon:
    steps = (
        np.linspace(0, 10, 20) / 10 / scaling_factor * min_pinch_size  
    )

    buffer = room
    # each iteration will more precisely identify the first self-intersection - two iterations should be enough
    stop_before_intersection = True
    for i in range(iterations):
        if buffer is None:
            return None
        if i == (iterations-1):
            stop_before_intersection = False
        # print("Stop before intersection: ", stop_before_intersection)
        buffer, step_size = marching_buffer(
            buffer, steps, stop_before_intersection=stop_before_intersection, iteration=i, plot=plot, fig=fig, ax=ax
        )
        steps = steps / step_reduction_factor

    if buffer is None:
        # print("No buffer found - returning None")
        return None
    
    # process the buffer and split the original room
    room_split = process_buffer(buffer, room, plot=plot, fig=fig, ax=ax)

    return room_split


def recursive_room_subdivision(room, scaling_factor:float, min_pinch_size:int=2.0, max_iters:int=5, no_parents=True, plot=False, fig=None, ax=None) -> list[dict]:
    reason = "Found all subdivisions for given params."
    sub_rooms = [
        {
            "id": "init_room",
            "geom": room,
            "level": 0,
            "parent": None,
            "subdivided": False,
            "children": [],
            "area": room.area
        }
    ]
    unprocessed_sub_rooms = [
    sub_room["id"] for sub_room in sub_rooms if not sub_room["subdivided"]
    ]

    i = 0
    while len(unprocessed_sub_rooms) > 0:
        sub_room_id = unprocessed_sub_rooms.pop(0)
        sub_room = [subroom for subroom in sub_rooms if subroom["id"] == sub_room_id][0]
        sub_room_geom = sub_room["geom"]
        sub_room_level = sub_room["level"]

        # subdivide the room
        try:
            subdivided_rooms = subdivide_room(
                sub_room_geom,
                min_pinch_size,
                scaling_factor,
                iterations=3,
                step_reduction_factor=10,
                plot=plot,
                fig=fig,
                ax=ax,
            )
        except Exception as e:
            print(f"Error: {e}")
            subdivided_rooms = None

        # print("Subdivided rooms: ", subdivided_rooms)

        if subdivided_rooms is not None:
            for j, sub_sub_room in enumerate(subdivided_rooms.geoms):
                new_sub_room = {
                    "id": f"{sub_room_id}_{j}",
                    "geom": MultiPolygon([sub_sub_room]),
                    "level": sub_room_level + 1,
                    "parent": sub_room_id,
                    "subdivided": False,
                    "children": [],
                    "area": sub_sub_room.area
                }
                sub_rooms.append(new_sub_room)

        # mark the sub_room as subdivided
        sub_room["subdivided"] = True

        # update the list of unprocessed sub_rooms
        unprocessed_sub_rooms = [
            sub_room["id"] for sub_room in sub_rooms if not sub_room["subdivided"]
        ]

        i += 1
        if i == max_iters:
            reason = "max iterations reached"
            break

    sub_rooms = parent_child_relationships(sub_rooms)

    if no_parents:
        # remove all sub_rooms which have children
        sub_rooms = [subroom for subroom in sub_rooms if len(subroom["children"]) == 0]

    sub_rooms_sorted = sorted(sub_rooms, key=lambda k: k["area"], reverse=True)

    return sub_rooms_sorted, reason


def parent_child_relationships(sub_rooms) -> list[dict]:
    # sort through items and create parent-child relationships

    for sub_room in sub_rooms:
        if sub_room["parent"] is not None:
            parent_id = sub_room["parent"]
            parent = [subroom for subroom in sub_rooms if subroom["id"] == parent_id][0]
            if "children" not in parent.keys():
                parent["children"] = []
            parent["children"].append(sub_room["id"])

    return sub_rooms
