# Transitland export for TransitCenter

This repo contains tools for exporting Transitland operators, routes, and stops within a given bounding box.

The output is a set of GeoJSON files, with each operator, route, or stop as a single feature. Additionally, routes and stops are annotated with basic information about headways.

# Usage: buildmsa.py

```
usage: buildmsa.py [-h] [--bbox BBOX] [--dates DATES] [--between BETWEEN]
                   [--departure_span DEPARTURE_SPAN]
                   [--headway_percentile HEADWAY_PERCENTILE]
                   [--high_frequency_headway HIGH_FREQUENCY_HEADWAY]
                   [--endpoint ENDPOINT] [--outpath OUTPATH]

Fetch operators, routes, stops for a bbox with frequency info

optional arguments:
  -h, --help            show this help message and exit
  --bbox BBOX           Bounding box, specified by coordinates: left,bottom,right,top
  --dates DATES         Dates to query for headways, comma separated, in the format YYYY-MM-DD
  --between BETWEEN     Start and end time to consider for headways
  --departure_span DEPARTURE_SPAN 
                        Duration each day that stop or route must have service
  --headway_percentile HEADWAY_PERCENTILE
                        Headway percentile, from 0.0 to 1.0, for high frequency service
  --high_frequency_headway HIGH_FREQUENCY_HEADWAY
                        Threshold, in seconds, for high frequency service
  --endpoint ENDPOINT   Transitland API endpoint
  --outpath OUTPATH     Output directory
```

The `buildmsa.py` script queries a given bounding box for operators, routes, and stops and stores the output as a set of GeoJSON files. The `--bbox` and `--dates` parameters are required.

## General options

The bounding box `--bbox` is specified using `left,bottom,right,top` coordinates. For example, `-123.024,37.107,-121.469,38.321` would cover part of the San Francisco Bay Area.

`--outpath` specifies a base directory for the output files. The directory will be created if it does not exist. The default is the current directory.

`--endpoint` provides the Transitland API endpoint; this will only be used for local debugging. The default is `http://transit.land`

## Headway calculation

Headways are defined by `origin:destination` pairs. This helps ensure that each direction of travel is considered separately, and helps when measuring interlined service. 

_Vermillion Route_

| Powell     | Montgomery | Embarcadero |
|------------|------------|-------------|
| 11:55      | 12:00      | 12:05       |
| 12:00      | 12:10      | 12:15       |
| 12:12      | 12:30      | 12:35       |
| 12:25      | 13:00      | 13:05       |

Consider the completely hypothetical schedule above. The stop pair `Montgomery:Embarcadero`, with trips between the two stops at `12:00, 12:10, 12:30, 13:00`, would have headways of `600, 1200, 1800`. Likewise, `Powell:Montgomery` with trips at `11:55, 12:00, 12:12, 12:25` would have headways `300, 720, 780`.

The headway reported will depend on the `--headway_percentile` argument. Using headways of `600, 1200, 1800`, the default value of `0.5` (median) would result in `1200`. A value of `1.0` would be a strict definition of service and return the longest observed headway of `1800`. A value of `0.0` would be the loosest definition and return the shortest observed headway of `600s`. [Linear interpolation](https://en.wikipedia.org/wiki/Percentile#The_linear_interpolation_between_closest_ranks_method) between closest values is used when necessary, `0.9` would result in a value of `1680`.

The `--high_frequency_headway` argument sets longest headway considered to be high frequency. This sets the `high_frequency=true` property in the GeoJSON output. If at least one stop pair in the result (at a given date, percentile, etc.) is less than `high_frequency_headway`, the route or stop is considered high frequency. For the example above, a value of `900` would result in `Powell:Montgomery` marked as high frequency, but not `Montgomery:Embarcadero`. A route is considered high frequency if any stop pairs in the route are high frequency, so the `Vermillion` route would be considered high frequency because `Powell:Montgomery` matches.

Additional arguments filter which trips are considered when calculating headways. 

The `--dates` argument specifies which days to use for calculating headways. For example, you could provide 5 consecutive days defining a work week, 2 days to measure weekend service, or any other combination. Trips on each given day will be used to generate headways, and all of these headways be used when calculating the percentile to report. For example, if a service has longer headways on Saturday and Sunday, and a strict `headway_percentile` of `0.9` is used, the resulting headway will most likely reflect the lower level of service on the weekends.

The `--between` argument lets you limit what period during each day will be used. For example, if you only wanted to count trips and headways between the hours of 7am and 10pm, you would provide `07:00,22:00`. This would ignore early morning and late evening trips, which might have a lower level of service. Conversely, value of `06:00,09:00` would only measure peak commute hour service.

Finally, the `--departure_span` argument provides a minimum amount of time that a service must be provided. For example, if you set the value to `14:00`, you would need to have two trips that connect a stop pair at least 14 hours apart on a given day. A commuter service might provide several trips in quick sequence, suggesting a short headway, but may not fit a definition of high frequency service that requires all day service.

Here is an [example API request](https://transit.land/api/v1/routes/r-9q9j-babybullet/headways?dates=2018-08-01&headway_percentile=0.5) measuring headways of the Caltrain Baby Bullet service.

## Examples

```
python buildmsa.py --bbox='-85.386,32.844,-83.269,34.617' --dates=2018-08-26,2018-08-27,2018-08-28,2018-08-29,2018-08-30,2018-08-21,2018-09-01 --between=07:00,22:00 --min_headway=900 --departure_span=14:00
```

This command would generate `operators.geojson`, `routes.geojson`, and `stops.geojson` output for a bounding box centered on Atlanta, Georgia. The output will include all routes and stops in the bounding box. For headway calculations and to mark features as high frequency, the full week of Aug 26, 2018 would be used to measure service, with trips between 7am and 10pm considered, and only stop pairs that have at least 14 hours of service each day.

# Usage: multimsas.py

```
usage: multimsas.py <input CSV file> <additional args>
```

This is a simple script that takes a CSV input file defining multiple regions, and generates `buildmsa.py` commands that can be run as a script or in parallel, e.g. using GNU `parallel`. The CSV should contain a header and the following columns: `msa_name, sw_lon, sw_lat, ne_lon, ne_lat`.

## Examples

```
python ./multimsas.py msa-bboxes/TC_Ridership_Viz_MSAs_with_bboxes.csv --dates=2018-08-26 --between=07:00,22:00
```

Would generate output like:

```
python buildmsa.py --outpath='results/Atlanta-Sandy Springs-Roswell, GA' --bbox='-85.386,32.844,-83.269,34.617' --dates=2018-08-26 --between=07:00,22:00
python buildmsa.py --outpath='results/Austin-Round Rock, TX' --bbox='-98.297,29.630,-97.024,30.906' --dates=2018-08-26 --between=07:00,22:00
python buildmsa.py --outpath='results/Baltimore-Columbia-Towson, MD' --bbox='-77.311,38.712,-75.747,39.721' --dates=2018-08-26 --between=07:00,22:00
...
```

# Output

## operators.geojson feature properties

API Response:

- onestop_id: A global unique Transitland identifier
- name: Operator name
- short_name: A short name for the operator
- website: Operator website
- country: Operator country
- state: Operator country
- metro: Operator metropolitan area, if known
- timezone: Operator default timezone
- represented_in_feed_onestop_ids: Imported from these Feeds

## routes.geojson feature properties

API response:

- onestop_id: A global unique Transitland identifier
- name: Route name
- vehicle_type: String representing the type of vehicle used the route, e.g. `bus` or `metro`.
- color: A hex color for displaying the route
- operated_by_onestop_id: Identifier for the operator
- operated_by_name: Name of the operator
- wheelchair_accessible: Wheelchair accessible, e.g. `all_trips`, `some_trips`, `no_trips`, or `unknown`
- bikes_allowed: Bicycles allowed, same values as `wheelchair_accessible`
- stops_served_by_route: Onestop IDs of stops served by this route
- route_stop_patterns_by_onestop_id: Route Stop Patterns (trip patterns) associated with this route

These values are generated by `buildmsa.py`:

- headways: Contents of `headways` API response
- min_headway: Lowest stop pair headway in `headways`
- high_frequency: The lowest stop pair headway is less than `--high_frequency_headway`

## stops.geojson feature properties

API Response:

- onestop_id: A global unique Transitland identifier
- name: Stop name
- timezone: Stop timezone
- osm_way_id: Currently associated OpenStreetMap Way ID
- served_by_vehicle_types: Visited by routes with these vehicle types
- wheelchair_boarding: Stop is wheelchair accessible
- operators_serving_stop: Stop is associated with these Operators
- routes_serving_stop: Stop is visited by these Routes

These values are generated by `buildmsa.py`:

- headways: Contents of `headways` API response
- min_headway: Lowest stop pair headway in `headways`
- high_frequency: The lowest stop pair headway is less than `--high_frequency_headway`
