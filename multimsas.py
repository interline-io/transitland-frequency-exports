import sys
import csv

args = sys.argv[2:]
args = ' '.join(args)

with open(sys.argv[1]) as f:
    reader = csv.DictReader(f)
    for row in reader:
        msa = row['msa_name']
        bbox = [row['sw_lon'], row['sw_lat'], row['ne_lon'], row['ne_lat']]
        bbox = ",".join(bbox)
        print "python buildmsa.py --outpath='results/%s' --bbox='%s' %s "%(msa,bbox,args)
