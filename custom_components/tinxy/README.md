# Tinxy addon for home assistant


Can be used for the smart switches from [Tinxy.in](https://tinxy.in/)

# Usage 


Install HACS

https://hacs.xyz/


Add repository to hacs 

```
https://github.com/arevindh/tinxy-hacs
```

Install Tinxy Smart Devices from hacs

Restart Home Assistant

Get the api key from application 

Go to Settings -> Integrations -> Search for Tixy 

When prompted Enter your key click next ,

Assing your devices to curresponding rooms , click finish


# Current issues

Due to the reponse delay via they api the toggle will have a delay for approx 3s . Status change can be adjusted using `scan_interval` parameter (better to keep this above `7` to avoid slowing the HA server)
