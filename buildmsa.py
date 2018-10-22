import json
import urllib
import urllib2
import datetime
import math
import os
import sys
import time
import argparse
from functools import wraps

# Retry decorator with exponential backoff
# https://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry  # true decorator
    return deco_retry

def get_headways(t, onestop_id, high_frequency_headway=None, **kw):
    headways = {}
    try:
        headways = ds.request('/api/v1/%s/%s/headways'%(t, onestop_id), **kw)
    except StandardError, e:
        print "Headways failed:", e
    if not headways:
        return {}
    high_frequency = False
    min_headway = sorted(headways.items(), key=lambda x:x[1])[0][1]
    print "min_headway: %s"%(min_headway)
    if high_frequency_headway and min_headway <= high_frequency_headway:
        print "high_frequency: %s"%(min_headway)
        high_frequency = True
    return dict(
        headways=headways,
        high_frequency=high_frequency,
        min_headway=min_headway   
    )

def write_geojson(filename, features):
    with open(filename, 'w') as f:
        fc = {'type':'FeatureCollection', 'features': features}
        json.dump(fc, f, indent=4, sort_keys=True)

class Datastore(object):
  """A simple interface to the Transitland Datastore."""
  def __init__(self, host):
    self.host = host

  @retry(urllib2.URLError, tries=1000, delay=3, backoff=1)
  def _request(self, uri):
    print uri
    req = urllib2.Request(uri)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req)
    return json.loads(response.read())

  def request(self, endpoint, **data):
    """Request with JSON response."""
    return self._request(
      '%s%s?%s'%(self.host, urllib.quote(endpoint), urllib.urlencode(data or {}))
    )

  def paginated(self, endpoint, key=None, **data):
    """Request with paginated JSON response. Returns generator."""
    key = key or endpoint.split('/')[-1]
    response = self.request(endpoint, **data)
    while response:
      meta = response['meta']
      print '%s: %s -> %s of %s'%(
        key,
        meta['offset'],
        meta['offset']+meta['per_page'],
        meta.get('total')
      )
      for entity in response[key]:
        yield entity
      if meta.get('next'):
        response = self._request(meta.get('next'))
      else:
        response = None

###############

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch operators, routes, stops for a bbox with frequency info')
    parser.add_argument('--bbox', help='Bounding box, specified by coordinates: left,bottom,right,top')
    parser.add_argument('--dates', help='Dates to query for headways, comma separated, in the format YYYY-MM-DD')
    parser.add_argument('--between', default="00:00,24:00", help='Start and end time to consider for headways')
    parser.add_argument('--departure_span', default="00:00", help='Duration each day that stop or route must have service')
    parser.add_argument('--headway_percentile', default="0.5", type=float, help='Headway percentile, from 0.0 to 1.0, for high frequency service')
    parser.add_argument('--high_frequency_headway', default=900, type=int, help='Threshold, in seconds, for high frequency service')
    parser.add_argument('--endpoint', default="https://transit.land", help='Transitland API endpoint')
    parser.add_argument('--outpath', default='.', help='Output directory')

    args = parser.parse_args()
    if not (args.bbox and args.dates):
        raise Exception("Requires bbox and at least one date")

    outpath = args.outpath
    try:
        os.makedirs(outpath)
    except OSError:
        pass

    ds = Datastore(args.endpoint)
    hw = dict(
        headway_dates=args.dates,
        headway_departure_between=args.between,
        headway_departure_span=args.departure_span,
        headway_percentile=args.headway_percentile,
        high_frequency_headway=args.high_frequency_headway
    )
    bp = dict(
        import_level=4, 
        imported_from_active_feed_version='true', 
        total='true',
        bbox=args.bbox
    )

    ##### Operators
    features = []
    for i in ds.paginated('/api/v1/operators', **bp):
        print i['onestop_id']
        feature = {'type':'Feature', 'geometry': i.pop('geometry'), 'properties': i}
        features.append(feature)
    write_geojson(os.path.join(outpath, 'operators.geojson'), features)

    ##### Routes
    features = []
    for c,i in enumerate(ds.paginated('/api/v1/routes', **bp)):
        print "route %s: %s"%(c, i['onestop_id'].encode('ascii', 'ignore'))
        i.update(get_headways('routes', i['onestop_id'], **hw))
        feature = {'type':'Feature', 'geometry': i.pop('geometry'), 'properties': i}
        features.append(feature)
    write_geojson(os.path.join(outpath, 'routes.geojson'), features)
    write_geojson(os.path.join(outpath, 'routes.high_frequency.geojson'), [i for i in features if i['properties'].get('high_frequency')])

    ##### Stops
    features = []
    for c,i in enumerate(ds.paginated('/api/v1/stops', **bp)):
        print "stop %s: %s"%(c, i['onestop_id'].encode('ascii', 'ignore'))
        i.update(get_headways('stops', i['onestop_id'], **hw))
        feature = {'type':'Feature', 'geometry': i.pop('geometry'), 'properties': i}
        features.append(feature)
    write_geojson(os.path.join(outpath, 'stops.geojson'), features)
    write_geojson(os.path.join(outpath, 'stops.high_frequency.geojson'), [i for i in features if i['properties'].get('high_frequency')])



