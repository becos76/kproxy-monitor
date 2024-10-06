# kproxy_monitor

## Overview

Just a way to ship kproxy status and metrics to kentik portal via NMS custom metrics by utilising the local healthcheck mechanism kproxy provides.
Once the metrics are in the portal, an NMS alerting policy could be set up to detect kproxy UP/DOWN from its Status.

## Requirements
- Kproxy must bind its healthcheck to a local IP or 0.0.0.0 in order to be pollable from the network. This is done via altering the default cli argument of `-healthcheck=127.0.0.1` to  `-healthcheck=0.0.0.0` in the service file or run command.

- Define the credentials and kproxy instances in the constants declaration section.

## Metrics and Dimensions

By default, everything will be reported under two measurements in metrics explorer:

- `/testing/agent/kproxy/`


| Type | Field | Description |
|:---: | :---: | --- |
| dimension | name  | kproxy name |
| dimension | ip    | kproxy IP |
| dimension | port  | HC listening port |
| dimension | state | as per table below |
| metric | status | [0,1,2,3] |
| metric | connected | number of connected devices
| metric | unregistered | number of unregistered devices |

- `/testing/agent/kproxy/devices`


| Type | Field | Description |
|:---: | :---: | --- |
| dimension | proxy_name    | kproxy name |
| dimension | proxy_ip      | kproxy IP |
| dimension | device_id     | device id |
| dimension | device_name   | device name |
| dimension | device_ip     | device IP |
| dimension | flow          | flow type |
| metric | In1 | incoming flow ratio 1s agg |
| metric | In15 | incoming flow ratio 15s agg  |
| metric | Out1 | outgoing flow ratio 1s agg |
| metric | Out15 | outgoing flow ratio 15s agg |


## Status and State

```
Status: (1) - Up    State: Operational
Status: (0) - Down  State: Connection Refused 
Status: (2) - Error State: No route to host 
Status: (2) - Error State: Timeout
Status: (2) - Error State: Other
Status: (3) - Error State: Not Good (not handled yet)
```

## ToDos (maybe)

- Implement logging :P
- Handle Unregistered devices list and ship details to portal
- Deploy as container along side kproxy one for local polling and reporting
- Expose prom metrics for scraping also
- Handle Last Seen and represent that as well