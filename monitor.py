#!/usr/bin/env python3

import subprocess
import time
import json
import string
import pingparsing
import logging
import multiprocessing as mp
from datetime import datetime
from typing import List

logging.basicConfig(filename='errors.log', filemode='w',
                    format='%(name)s: %(levelname)s: %(message)s')


class Device:
    def __init__(self, name, ip: str, mac, manufacturer, hardware, location):
        if not (name or ip):
            raise Exception('A device must have a name and an IP.')

        self.name = name
        self.ip: str = ip
        self.mac = mac
        self.manufacturer = manufacturer
        self.hardware = hardware
        self.location = location

        self.ping_data = dict()

    def refresh(self) -> 'Device':
        self._ping()

        # Todo: Add more detailed device status checks here.

        return self

    def _ping(self):
        # ping the device
        response = subprocess.run(['ping', '-c 1', self.ip],
                                  stdout=subprocess.PIPE)

        if response.returncode == 0:
            # success; parse and store the response
            p = pingparsing.PingParsing()
            self.ping_data = p.parse(response.stdout).as_dict()

        else:
            # error; invalidate ping status and log the exception
            self.ping_data = dict()

            logging.error('Error while pinging %s (%s): \"%s\"' %
                          (str(self), self.ip, response.stdout))

    def okay(self) -> bool:
        # packet_loss_count must be 0 for good device status
        good = self.ping_data.get('packet_loss_count', 1) == 0

        # Todo: Make the status dependent on more than just ping packet loss.

        return good

    def __repr__(self):
        return 'Device(%s, %s, %s, %s, %s, %s)' % (
            self.name, self.ip, self.mac,
            self.manufacturer, self.hardware, self.location
        )

    def __str__(self):
        # eg, "Lamp in the Entryway"
        return '%s in the %s' % (self.name, self.location)


class SmartHome:
    def __init__(self, name, devices: List[Device] = None):
        self.name = name
        self.devices = devices or list()

    def refresh(self):
        # Todo: Add non device-specific status checks here.
        # ARP checks? https://stackoverflow.com/questions/1750803/
        # obtain-mac-address-from-devices-using-python
        # figure out router ip, try pinging router; try pinging internet?

        def _refresh_device(device: Device):
            device.refresh()

        # spin up worker processes to check each device
        with mp.Pool() as pool:
            # mp.Manager() turns the devices list into a shared resource
            self.devices = pool.map(Device.refresh,
                                    mp.Manager().list(self.devices))


def monitor(home: SmartHome, interval: int):
    # 'a+' == append to file, create file if not found
    with open('status.log', 'a+') as statusfile:

        # print the status file header
        letters = string.ascii_uppercase
        for i, d in enumerate(home.devices):
            statusfile.write('%s = %s\n' % (letters[i], d))
        letters_str = ' '.join(letters[:len(home.devices)])
        statusfile.write('\n' + (' '*22) + letters_str + '\n')

        while True:
            # generate a path for the errors logfile
            timestamp = datetime.now()

            # refresh the smart home
            home.refresh()

            # update the status logfile
            ts_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            stat_str = ' '.join(['x' if d.okay() else ' '
                                 for d in home.devices])
            statusfile.write('%s   %s\n' % (ts_str, stat_str))
            statusfile.flush()

            # sleep for [interval] seconds
            time.sleep(interval)


if __name__ == '__main__':
    # load the devices from json
    devices = json.loads(open('devices.json').read())
    devices = [Device(**device) for device in devices]

    # build the home
    home = SmartHome('MyHome', devices)

    # monitor home status
    interval = 60  # seconds
    monitor(home, interval)
