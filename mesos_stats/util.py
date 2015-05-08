import json
import time
import requests

def try_get_json(url):
    try:
        return json.loads(requests.get(url).text)
    except requests.exceptions.ConnectionError as e:
        log("GET %s failed: %s" % (url, e))
        raise
    except requests.exceptions.ReadTimeout:
        log("GET %s timed out." % url)
        raise
   
def log(message):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print '%s %s' % (ts, message)

