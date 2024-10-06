import asyncio
import socket
from datetime import datetime
from pprint import pprint as pp
from ttp import ttp
from influxdb_client import Point
import requests


#
# Define constants
#############################################
URL = "https://grpc.api.kentik.eu/kmetrics/v202207/metrics/api/v2/write?bucket=&org=&precision=ns"
HEADERS = {
        "Content-type": "application/influx",
        "X-Ch-Auth-Email": "< portal email >",
        "X-Ch-Auth-API-Token": "< portal token >",
}
PROXIES = [
    { 'name': 'kproxy_sandbox02', 'ip': '192.168.11.3', 'port': 9996 },
]
MODEL = "/testing/kproxy"
FREQUENCY = 300 # poll every 5 mins
###############################################

def netcat(proxy):
    """ Connect to kproxy HC port and get the status
    """  
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4)
        s.connect((proxy['ip'], proxy['port']))
        s.shutdown(socket.SHUT_WR)
    except ConnectionRefusedError:
        proxy['status'], proxy['state'] = 0, "Connection Refused"
        return False
    except TimeoutError:
        proxy['status'], proxy['state'] = 2, "Timeout"
        return False
    except OSError:
        proxy['status'], proxy['state'] = 2, "No route to host"
        return False
    except:
        proxy['status'], proxy['state'] = 2, "Other"
        return False
    
    while True:
        data = s.recv(4096)
        if not data:
            break
        recv = data.decode('utf-8')
    s.close()
           
    proxy['status'] = 1
    proxy['health'] = recv
    return True

def process_initial(metrics,proxy):
    """ Extract common metrics for all kproxy states
    """
    tags = [ 'name', 'ip', 'port', 'state']
    fields = ['status']    
    metrics.update({ 'tags': dict([ (k,proxy[k]) for k in tags ]) })
    metrics.update({ 'fields': dict([ (k,proxy[k]) for k in fields ]) })

def process_full(metrics, proxy):
    """ Extract additional metrics for operational kproxies, like devices
    """
    fields = ['connected', 'unregistered']
    metrics.update( { 'fields': metrics['fields'] | dict([ (k,int(proxy[k])) for k in fields ]) })
    
    if proxy['hc'] != "GOOD":
        print(f"{proxy['name']} Healtchcheck is not GOOD")
    if proxy.get('devices'):
        if metrics['fields']['connected'] != len(proxy['devices']):
            print(f"{proxy['name']} Connected device number does not match")
        else:
            post_metrics(metrics)
            for device in proxy['devices']:
                process_devices(device,proxy)
    
    
def post_metrics(metrics):
    """ Port the metrics via influx line to kentik
    """
    point = Point.from_dict(metrics)
    try:
        #pp(point.to_line_protocol())
        re = requests.post(URL, headers=HEADERS, data=point.to_line_protocol(), timeout=5)
        re.raise_for_status()
        if re.status_code != 204:
            raise requests.exceptions.HTTPError
    except requests.exceptions.HTTPError as err:
        print("Posting metrics failed.", err)


def process_devices(device,proxy):
    """ Extract per reported device metrics
    """
    device_metrics = {'measurement' : MODEL+"/devices", 'tags': {}, 'fields': {}}
    tags = [ 'device_id', 'device_name', 'device_ip', 'flow' ]
    fields = [ 'In1', 'In15', 'Out1', 'Out15' ]

    device_metrics.update({'tags': { 'proxy_name': proxy['name'], 'proxy_ip': proxy['ip'] }})
    device_metrics.update({ 'tags': device_metrics['tags'] | dict([ (k,device[k]) for k in tags ]) })
    device_metrics.update({ 'fields': dict([ (k,device[k]) for k in fields ]) })
    post_metrics(device_metrics)
        
async def periodic(interval, coroutine, *args, **kwargs):
    while True:
        await asyncio.sleep(interval)
        await coroutine(*args, **kwargs)


async def poll_device(proxy):
    metrics = {'measurement' : MODEL, 'tags': {}, 'fields': {}}
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print(now,"Polling ", proxy['name'])
    if netcat(proxy):
        proxy['state'] = "Operational"
        print(f"{proxy['name']} is {proxy['state']}")
        process_initial(metrics, proxy)
        parser = ttp(data=proxy['health'], template="templates/kproxy.ttp")
        parser.parse()
        proxy.update(parser.result()[0][0][0])
        process_full(metrics, proxy)
    else:
        print(f"{proxy['name']} error --{proxy['state']}--")
        process_initial(metrics, proxy)
        post_metrics(metrics)
        

async def main():
    tasks = []
    try:
        for proxy in PROXIES:
            tasks.append(asyncio.create_task(periodic(FREQUENCY,poll_device,proxy)))
        await asyncio.gather(*tasks)    
    except KeyboardInterrupt:
        SystemExit()


if __name__ == "__main__":
    asyncio.run(main())

    