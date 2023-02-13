import itertools
import json
import logging
import random
import sys

import click
import earcut.earcut as earcut
import numpy

from .densities import densities


def randround(x):
    return int(x + random.random())


def random_points(triangle, k):

    u = numpy.random.rand(k, 2)

    invert = u.sum(axis=1) > 1
    u[invert, :] = 1 - u[invert, :]

    a = triangle[1, :] - triangle[0, :]
    b = triangle[2, :] - triangle[0, :]

    pts = triangle[0, :] + u @ numpy.c_[a, b]

    return pts


def triangulate_geometry(geometry):

    triangles = numpy.empty((0, 3, 2))

    if geometry["type"] == "Polygon":
        triangles = triangulate_polygon(geometry["coordinates"])
    elif geometry["type"] == "MultiPolygon":
        for polygon_coords in geometry["coordinates"]:
            polygon_triangles = triangulate_polygon(polygon_coords)
            triangles = numpy.vstack((triangles, polygon_triangles))

    return triangles


def triangulate_polygon(geojson_coords):

    flattened_coords = earcut.flatten(geojson_coords)["vertices"]

    triangle_indices = numpy.reshape(earcut.earcut(flattened_coords), (-1, 3))
    coords = numpy.reshape(flattened_coords, (-1, 2))

    return coords[triangle_indices]


def areas(triangles):

    ab = triangles[:, 1, :] - triangles[:, 0, :]
    ac = triangles[:, 2, :] - triangles[:, 0, :]

    return numpy.abs(numpy.cross(ab, ac) / 2)


def points_in_feature(feature, n_points):

    polygon_points = []

    triangles = triangulate_geometry(feature["geometry"])
    weights = areas(triangles)
    nans = numpy.isnan(weights)
    triangles = triangles[~nans]
    weights = weights[~nans]

    weights /= weights.sum()

    points_per_triangles = numpy.random.multinomial(n_points, weights)
    triangles_with_points = points_per_triangles.nonzero()[0]

    for i in triangles_with_points:
        triangle = triangles[i, :, :]
        points_per_triangle = points_per_triangles[i]
        points = random_points(triangle, points_per_triangle)
        polygon_points.extend(points.tolist())

    return polygon_points


@click.command()
@click.argument("infile", type=click.File("r"), nargs=1)
@click.option("--units-per-dot", type=int, nargs=1, default=1)
@click.option("--population-variable", type=str, nargs=1, default=None)
@click.option("--population-expression", type=str, nargs=1, default=None)
def main(infile, units_per_dot, population_variable, population_expression):

    logging.basicConfig(level=logging.INFO)

    derive_pop = None

    if population_variable is None and population_expression is None:
        population_variable = "p1_001n"
    elif population_variable is not None and population_expression is None:
        pass
    elif population_variable is None and population_expression is not None:
        population_variable = "__generated"
        derive_pop = eval("lambda d:" + population_expression)
    else:
        raise click.UsageError(
            "you cannot set both --population-variable and --population-expression"
        )

    blocks = json.load(infile)

    if derive_pop is not None:
        for feature in blocks["features"]:
            feature["properties"][population_variable] = derive_pop(
                feature["properties"]
            )

    landuse_densities = densities(blocks["features"], population_variable)

    multipoint = []

    def block_key(feature):
        return (
            feature["properties"]["geoid"],
            feature["properties"][population_variable],
        )

    for (_, population), components_g in itertools.groupby(
        blocks["features"], block_key
    ):
        components = list(components_g)

        land_use_weights = numpy.array(
            [
                component["properties"]["intersection_area"]
                * landuse_densities[component["properties"]["landuse"]]
                for component in components
            ]
        )
        land_use_weights /= land_use_weights.sum()

        points_per_component = numpy.random.multinomial(
            randround(population / units_per_dot), land_use_weights
        )

        for i, component in enumerate(components):

            if (k := points_per_component[i]) > 0:
                points = points_in_feature(component, k)
                multipoint.extend(points)

    geojson_points = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPoint",
                    "coordinates": multipoint,
                    "properties": {},
                },
            }
        ],
    }

    json.dump(geojson_points, sys.stdout)
