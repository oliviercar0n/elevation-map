import glob
import json
import pandas as pd
import shapefile
from pyproj import Transformer
from shapely.geometry.polygon import Polygon
from shapely.geometry import Point
import matplotlib.pyplot as plt
import time

from elevation import get_elevation_from_coordinates

LAT_BINS = 75
LON_BINS = 300
SCALE_FACTOR = 8

# Read Shapefile
shp = shapefile.Reader("shp/terre_shp.shp")

# Extract city of Montreal shape perimeter
feature = shp.shapeRecords()[33]
geometry = feature.shape.__geo_interface__
perimeter = geometry['coordinates'][0]

# Transform to ESPG 4326 projection
transformer = Transformer.from_crs("NAD83_MTM_zone_8","epsg:4326")
points = [transformer.transform(point[0],point[1]) for point in perimeter]

# Create Polygon from perimeter
polygon = Polygon(points)
min_lat, min_lon, max_lat, max_lon = polygon.bounds

# Calculate latitude and longitude increment sizes
lon_range = abs(max_lon-min_lon)
lat_range = abs(max_lat-min_lat)

lat_incr = lat_range/LAT_BINS
lon_incr = lon_range/LON_BINS

# Create dataset of points within the polygon and regular intervals based on bin sizes
data = []
total_break = 0
for y in range(LAT_BINS):
    lat_bin_min = min_lat + y*lat_incr
    lat_bin_max = min_lat + (y+1)*lat_incr

    lon_bin_all = [point[1] for point in points if point[0] > lat_bin_min and point[0] < lat_bin_max]
    
    lon_bin_max = max(lon_bin_all)
    lon_bin_min = min(lon_bin_all)
    lon_bin_range = lon_bin_max-lon_bin_min
    lon_bin_incr = lon_bin_range/lon_incr
    lon_bin_incr_cnt = int(lon_bin_incr)
    
    line_break = False
    break_cnt = 0
    for x in range(lon_bin_incr_cnt):
        point_lat = round(lat_bin_min,6)
        point_lon = round(lon_bin_min+x*lon_incr,6)
        curr_point = Point(point_lat,point_lon)
        if polygon.contains(curr_point):
            if line_break:
                line_break = False
                break_cnt += 1

            data.append([y+1,y+1+break_cnt+total_break, point_lat, point_lon])
        else:
            line_break = True
    total_break += break_cnt

elevation_points = pd.DataFrame(data,columns=['BinID','RowID','Latitude','Longitude'])

# Get elevation data from Jawg Elevation API    
chunk_size = 500
for i in range(0,len(elevation_points), chunk_size):
    subset = elevation_points.iloc[i:i+chunk_size]
    coordinates = list(zip(subset.Latitude, subset.Longitude))
    data = get_elevation_from_coordinates(coordinates)
    with open(f'json/elevation_{i}.json', 'w') as f:
        json.dump(data, f)
    time.sleep(5)

# Assemble all elevation data into a dataframe
raw = []
for file in glob.glob('json/*.json'):
    with open(file) as f:
        data = json.load(f)
    for item in data:
        raw.append([item['elevation'],item['location']['lat'],item['location']['lng'],item['resolution']])

df_elev = pd.DataFrame(raw, columns = ['Elevation','Lat','Lon','Resolution'])

# Merge elevation and points dataframes
elevation_data = pd.merge(elevation_points, df_elev, how = 'left', left_on=['Latitude','Longitude'], right_on=['Lat','Lon'])
elevation_data= elevation_data[['RowID','Latitude','Longitude','Elevation']]

# Apply scaling factor to accentuate terrain features
min_elev = min(elevation_data['Elevation'])
max_elev = max(elevation_data['Elevation'])

elevation_data['Elevation_Scaled'] = elevation_data['Elevation']/max_elev*SCALE_FACTOR
elevation_data['Latitude_Elev'] = elevation_data['Latitude'] + elevation_data['Elevation_Scaled']*lat_incr

# Plot final map
fig, ax = plt.subplots(figsize =(60,44))
ax.set_facecolor('#0f0f0f')
ax.grid(False)
for z in range(LAT_BINS+total_break):
    dftmp = elevation_data[(elevation_data['RowID'] == z+1) & (elevation_data['Elevation'] >0) ]
    if len(dftmp) > 5:
        ax.plot(dftmp['Longitude'],dftmp['Latitude_Elev'],linestyle = 'solid',c= 'w',linewidth=3.0)

plt.axis('off')
plt.savefig('mtl_elevation.png',pad_inches=0,facecolor = '#0f0f0f',bbox_inches = 'tight')