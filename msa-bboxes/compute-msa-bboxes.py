import csv
import fiona
import shapely
from shapely.geometry import shape
import pprint

msa_bboxes = {}

with fiona.open('cb_2017_us_cbsa_500k/cb_2017_us_cbsa_500k.shp', 'r') as msa_polygons:
  for msa_polygon in msa_polygons:
    name = msa_polygon['properties']['NAME']    
    name = name.replace('--', '-')
    name = name.replace('–', '-')
    bbox = shapely.geometry.shape(msa_polygon['geometry']).bounds
    msa_bboxes[name] = bbox

with open('TC_Ridership_Viz_MSAs.csv', newline='') as input, open('TC_Ridership_Viz_MSAs_with_bboxes.csv', 'w') as output:
  reader = csv.reader(input)
  next(reader, None) # skip incoming headers
  writer = csv.writer(output)
  writer.writerow(['msa_name', 'sw_lon', 'sw_lat', 'ne_lon', 'ne_lat']) # write new headers
  for row in reader:
    name = row[0]
    name = name.replace('--', '-')
    name = name.replace('–', '-')
    name = name.replace('Raleigh-Cary', 'Raleigh')
    name = name.replace('Louisville-Jefferson', 'Louisville/Jefferson')
    bbox = msa_bboxes.get(name, [])
    writer.writerow([row[0], *bbox])

