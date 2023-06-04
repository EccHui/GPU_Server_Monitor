import network, time, json
from tftlcd import LCD15
from machine import Pin
from libs.urllib.urequest import urlopen

# define commonly used colors
RED    = (255,  0,  0)
GREEN  = (  0,255,  0)
BLUE   = (  0,  0,255)
YELLOW = (255,255,  0)
BLACK  = (  0,  0,  0)
WHITE  = (255,255,255)
# my configurations
BG_COLOR = BLACK
FG_COLOR = WHITE
# configure hosts
HOSTS = [
    {"http://xx.xx.xx.xx:9988/": "GPU-Server-A",},
    {"http://xx.xx.xx.xx:9988/": "GPU-Server-B",},
    {"http://xx.xx.xx.xx:9988/": "GPU-Server-C",}
]
MAX_GPU_PER_HOST = 8

# start of WIFI_Connect()
def WIFI_Connect():
    WIFI_LED = Pin(2, Pin.OUT)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    start_time = time.time()
    
    if not wlan.isconnected():
        print('connecting to network')
        # SSID and password for WIFI
        wlan.connect('ZTE-uu36bh', 'lab1710lab1710')
        while not wlan.isconnected():
            # lighten LED
            WIFI_LED.value(1)
            time.sleep_ms(300)
            WIFI_LED.value(0)
            time.sleep_ms(300)
            
            if time.time() - start_time > 15:
                print('WIFI Connected Timeout!')
                wlan.active(False)
                break

    if wlan.isconnected():
        WIFI_LED.value(1)
        print('network information:', wlan.ifconfig())
        d.printStr('IP/Subnet/GW:', 10, 20, color=BLUE, size=1)
        d.printStr(wlan.ifconfig()[0], 10, 70, color=WHITE, size=1)
        d.printStr(wlan.ifconfig()[1], 10, 90, color=WHITE, size=1)
        d.printStr(wlan.ifconfig()[2], 10, 110, color=WHITE, size=1)
# end of WIFI_Connect()

# start of GPUStat_Get()
def GPUStat_Get(hosts):
    gpustats = []
    for url in hosts:
        try:
            raw_resp = urlopen(url + 'gpustat')
            gpustat = json.loads(raw_resp.read())
            raw_resp.close()
            if not gpustat or 'gpus' not in gpustat:
                continue
            if hosts[url] != url:
                gpustat['hostname'] = hosts[url]
            gpustats.append(gpustat)
        except Exception as e:
            print('Error: %s getting gpustat from %s' %
                  (getattr(e, 'message', str(e)), url))
    try:
        sorted_gpustats = sorted(gpustats, key=lambda g: g['hostname'])
        if sorted_gpustats is not None:
            return sorted_gpustats
    except Exception as e:
        print("Error: %s" % getattr(e, 'message', str(e)))
    return gpustats
# end of GPUStat_Get()

def abrev(name):
  sname_list = ['3090', 'V100']
  for sname in sname_list:
    if sname in name:
      return sname
  return name

# start of GPUInfo_Get()
def GPUInfo_Get(gpustats):
    if gpustats is None:
        raise ValueError
    
    gpuinfos = []; gputmps = []
    for stat in gpustats:
        info = [f"Host Name: {stat['hostname']}",
                f"Time: {stat['query_time'].split('.')[0].replace('T', ' ')}"]
        tmp = []
        for gpu in stat['gpus']:
            s = f"[{gpu['index']}] {abrev(gpu['name'])} | " +\
                f"{gpu['temperature.gpu']:2d} C, {gpu['utilization.gpu']:3d} % | " +\
                f"{round(gpu['memory.used']/1024):2d}/{round(gpu['memory.total']/1024):2d} GB | "
            for p in gpu['processes']:
                if p['gpu_memory_usage'] > 1024:
                    s += f"{p['username']}({round(p['gpu_memory_usage']/1024):d}G) "
            info.append(s)
            tmp.append(gpu['temperature.gpu'])
        gpuinfos.append(info)
        gputmps.append(tmp)
    return gpuinfos, gputmps
# end of GPUInfo_Get()

def Color_Get(temperature):
    if temperature <= 25:
        color = BLUE
    elif temperature <= 50:
        color = GREEN
    elif temperature <= 75:
        color = YELLOW
    else:
        color = RED
    return color

# start of LCD_Show()
def LCD_Show(gpuinfos, temperatures, d):
    for info, temp in zip(gpuinfos, temperatures):
        d.printStr(info[0], 10, 20, FG_COLOR, size=1)
        d.printStr(info[1], 10, 40, FG_COLOR, size=1)
        info = info[2:]
        max_char_num = 27
        info_max_len = 0
        for fo in info:
            if len(fo) > info_max_len:
                info_max_len = len(fo)
        for i, s in enumerate(info):
            d.printStr(s[0:4], 10, 70 + 20 * i, FG_COLOR, size = 1)
        for b in range(info_max_len - max_char_num):
            for i, s in enumerate(info):
                d.printStr(s[b+4:b+max_char_num], 42, 70 + 20 * i, Color_Get(temp[i]), size = 1)
                if i > MAX_GPU_PER_HOST: # limited by screen size
                    break
            if b == 0:
                if i < MAX_GPU_PER_HOST - 1:
                    for j in range(i+1, MAX_GPU_PER_HOST):
                        d.printStr(s[:max_char_num], 10, 70 + 20 * j, BG_COLOR, size = 1)
                time.sleep(1)
            else:
                time.sleep(0.1)
# end of LCD_Show()

def LCD_IMG(d, img_pth):
    d.Picture(0, 0, img_pth)
    
def fun(KEY):
    global state
    time.sleep_ms(10)
    if KEY.value() == 0:
        state = not state

# configure LCD screen: vertical display
d = LCD15(portrait=1)
# configure external interrupt
KEY = Pin(9, Pin.IN, Pin.PULL_UP)
KEY.irq(fun, Pin.IRQ_FALLING)
state = 0
# configure WIFI connection
WIFI_Connect()
# count
count = 0
flag = 0
while True:
    if state == 0:
        if flag != 0:
            d.fill(BG_COLOR)
            flag = 0
        STATS = GPUStat_Get(HOSTS[count])
        INFO, TMP = GPUInfo_Get(STATS)
        LCD_Show(INFO, TMP, d)
        if count == 2:
            count = 0
        else:
            count += 1
    else:
        if flag == 0:
            LCD_IMG(d, "cxk.jpg")
            flag = 1
