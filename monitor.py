import subprocess
import time
import json
import string
import pingparsing
from datetime import datetime
from typing import List, Dict


class Device:
    def __init__(self, name, ip: str, mac,
                 manufacturer, hardware, location):
        self.name = name
        self.ip: str = ip
        self.mac = mac
        self.manufacturer = manufacturer
        self.hardware = hardware
        self.location = location

    def __hash__(self):
        return hash(repr(self))

    def __repr__(self):
        return 'Device(%s, %s, %s, %s, %s, %s)' % (
            self.name, self.ip, self.mac,
            self.manufacturer, self.hardware, self.location
        )

    def __str__(self):
        # eg, "Ben's Lamp in the Entryway"
        return '%s in the %s' % (self.name, self.location)


class DeviceStatus:
    def __init__(self):
        self.ping: Dict = {}

    def ok(self) -> bool:
        return self.ping['packet_loss_count'] == 0

        # TODO: Extend as other statuses are added...


class SmartHome:
    def __init__(self, name, devices: List[Device]):
        self.name = name
        # devices is a mapping of Device -> DeviceStatus
        self.devices = {d: DeviceStatus() for d in devices}

    def check_status(self, logfile_path=None):
        # ping all devices
        self.pingall(logfile_path)

        # TODO: Add any other status checks...

    def pingall(self, logfile_path=None):
        for d in self.devices:
            # ping the device
            response = subprocess.run(['ping', '-c 1', d.ip],
                                      stdout=subprocess.PIPE)

            # parse and store the response
            p = pingparsing.PingParsing()
            self.devices[d].ping = p.parse(response.stdout).as_dict()

            # log any errors, if requested
            if logfile_path and not self.devices[d].ok():
                # 'ab+' == append binary str, create file if not found
                with open(logfile_path, 'ab+') as logfile:
                    logfile.write(response.stdout + b'\n')


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
            logpath = timestamp.strftime('logs/%Y-%m-%d %H.%M.%S.log')

            # update the status of the smart home
            home.check_status(logpath)

            # update the status logfile
            ts_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            stat_str = ' '.join(['x' if status.ok() else ' '
                                 for _, status in home.devices.items()])
            statusfile.write('%s   %s\n' % (ts_str, stat_str))
            statusfile.flush()

            # sleep for [interval] seconds
            time.sleep(interval)


if __name__ == '__main__':
    # load the devices from json
    _devices = json.loads(open('devices.json').read())
    _devices = [Device(**_device) for _device in _devices]

    # build the home
    _home = SmartHome('FultonHome', _devices)

    # monitor home status
    interval = 5 * 60  # seconds
    monitor(_home, interval)
