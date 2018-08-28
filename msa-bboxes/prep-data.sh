# see https://www.census.gov/geo/maps-data/data/cbf/cbf_msa.html
wget http://www2.census.gov/geo/tiger/GENZ2017/shp/cb_2017_us_cbsa_500k.zip
unzip cb_2017_us_cbsa_500k.zip -d cb_2017_us_cbsa_500k
rm -f cb_2017_us_cbsa_500k.zip
# ogr2ogr -f GeoJSON -t_srs crs:84 cb_2017_us_cbsa_500k.geojson cb_2017_us_cbsa_500k/cb_2017_us_cbsa_500k.shp 