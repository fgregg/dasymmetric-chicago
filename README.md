# Chicago Dots
*the finest dots for Chicago*

<img src="https://user-images.githubusercontent.com/536941/218774150-04f2121d-d834-4eb7-8437-a384659d422c.png" height="300">


| | Full Population | Over-18 Population | Under-18 Population |
|-|-|-|-|
| 1 person per point | <a href="./points/points_full_1.geojson" download="points_full_1.geojson">points_full_1.geojson</a> (54M) | <a href="./points/points_over_18_1.geojson" download="points_over_18_1.geojson">points_over_18_1.geojson</a> (44M) | <a href="./points/points_under_18_1.geojson" download="points_under_18_1.geojson">points_under_18_1.geojson</a> (11M) |
| 5 people per point | <a href="./points/points_full_5.geojson" download="points_full_5.geojson">points_full_5.geojson</a> (11M) | <a href="./points/points_over_18_5.geojson" download="points_over_18_5.geojson">points_over_18_5.geojson</a> (8.7M) | <a href="./points/points_under_18_5.geojson" download="points_under_18_5.geojson">points_under_18_5.geojson</a> (2.2M) |
| 10 people per point | <a href="./points/points_full_10.geojson" download="points_full_10.geojson">points_full_10.geojson</a> (5.4M) | <a href="./points/points_over_18_10.geojson" download="points_over_18_10.geojson">points_over_18_10.geojson</a> (4.4M) | <a href="./points/points_under_18_10.geojson" download="points_under_18_10.geojson">points_under_18_10.geojson</a> (1.1M) |
| 50 people per point | <a href="./points/points_full_50.geojson" download="points_full_1.geojson">points_full_50.geojson</a> (1.1M) | <a href="./points/points_over_18_50.geojson" download="points_over_18_50.geojson">points_over_18_50.geojson</a> (890K) | <a href="./points/points_under_18_50.geojson" download="points_under_18_50.geojson">points_under_18_50.geojson</a> (221K) |
| 100 people per point | <a href="./points/points_full_100.geojson" download="points_full_100.geojson">points_full_100.geojson</a> (560K) | <a href="./points/points_over_18_100.geojson" download="points_over_18_100.geojson">points_over_18_100.geojson</a> (449K) | <a href="./points/points_under_18_100.geojson" download="points_under_18_100.geojson">points_under_18_100.geojson</a> (111K) |

## What is this?

[Dot density maps](https://en.wikipedia.org/wiki/Dot_distribution_map) are a great way to show the distribution of countable things across a map. 

The usual approach is to randomly generate N points within a boundary, where N is proportional to the number you want to show, i.e. the number of people who live in a census block or the number of people who voted for a candidate in election precinct.

But boundaries are often quite weird, and that approach can mean we put dots in the lake or the middle of the highway. If the data we are mapping is related to where people live, it would be nice to put the dots where people are likely to be. That's what this project is here to help you do, at least for Chicago.

## Approach
The U.S. Decennial Census gives us high-resolution data on the number of people who live in a census "block," which often looks like a real city block in Chicago. 

We start with this block data and then use [dasymetric mapping](https://en.wikipedia.org/wiki/Dasymetric_map) to refine the block data with auxillary data.

First we use [CMAP's remarkable land use data set](https://www.cmap.illinois.gov/data/land-use) that classifies how land is being used at the parcel level.

We then further subdivide the landuse data into the portions that intersect with [buildings footprints](https://data.cityofchicago.org/Buildings/Building-Footprints-current-/hz9b-7nh8) and the portions that do not intersect with any buildings. We use [non-negative linear regression](https://en.wikipedia.org/wiki/Non-negative_least_squares) to estimate the population density of the different classes of landuses in both their building-intersection and building-difference variants.

With all this data prepared, we then take the following steps:

1. For each 2020 census block in Chicago, divide it into subareas of different land uses, building footprints, and non-empty land.
2. Then, allocate the block population to each subarea in rough proportion to the area of the subarea multiplied by the estimated population density of that land use category. 
3. Finally, randomly generate points in each subarea.

## Example: votes by precincts
These maps show the number of votes for Toni Preckwinkle in the February 2019 mayoral elections, by electoral precinct in the 5th ward. The 5th ward includes many large parks and non-residential areas.  The map on the left uses uniformly random points within the precincts. The map on the right uses dasymetric dots from this project. 

| uniformly random dots | dasymetric dots |
|-|-|
|<img src="https://user-images.githubusercontent.com/536941/218846808-a8702422-3775-4ab9-9280-c67a55b1e777.png" >|<img src="https://user-images.githubusercontent.com/536941/218846743-1dfdf401-ff2e-437a-9895-b930876efeb6.png">|

## How to use
For each area you want to N point for, you will find the dasymetric points that intersect with the area. Then take N of those points.

Here's how you might do it in PostGIS (assuming you downloaded an imported a GeoJSON file):

```sql
SELECT precinct_id, geom
FROM (
  SELECT precincts.id AS precinct_id, points_full_1.geom AS geom,
         ROW_NUMBER() OVER (PARTITION BY precincts.id) AS point_num,
         precincts.n_votes
  FROM precincts
  JOIN points_full_1 ON ST_Intersects(precincts.geom, points_full_1.geom)
) AS intersections
WHERE point_num <= n_votes;
```

or with Python along with geopandas and shapely:

```python
import geopandas as gpd

# Load the polygons and points into GeoDataFrames
polygons = gpd.read_file('path/to/precincts.geojson')
multipoint = gpd.read_file('path/to/points_full_1.geojson')

# Turn into points
points = multipoint.explode(index_parts=True)

# Perform the spatial join to find the intersections
intersections = gpd.sjoin(points, polygons, op='intersects')

# Group by polygon and sample arbitrary points
arbitrary_points = intersections.groupby('index_right').apply(lambda x: x.sample(n=x.iloc[0]['TONI PRECKWINKLE'], replace=True)).reset_index(drop=True)
```

## To build data youself

### system requirements
* wget
* gdal
* gdal-bin
* libgdal-dev
* libsqlite3-mod-spatialite
* spatialite-bin

```console
> git clone git@github.com:fgregg/chicago-dots.git
> cd chicago-dots
> pip install -e .
> make
```

## Code
[github](https://github.com/fgregg/chicago-dots)

## Thanks
The random point generation is adapted from [Ben Schmidt's dot density code](https://observablehq.com/@bmschmidt/dot-density). 
