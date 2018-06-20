# -*- coding: utf-8 -*-
# Description:
# Setup for the OSP netstat Server
#
# Authors:
# Jan-Oliver Wagner <Jan-Oliver.Wagner@greenbone.net>
#
# Copyright:
# Copyright (C) 2015 Greenbone Networks GmbH
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.

from ospd.ospd_ssh import OSPDaemonSimpleSSH
from ospd.misc import main as daemon_main
from ospd_netstat import __version__

OSPD_DESC = """
This scanner runs the tool 'netstat' on the target hosts via a ssh connection.

This tool is commonly available on most linuxoid systems and collects the open ports,
bound interfaces and processes of running services.

For executing netstat a low privileged user account is sufficient.
However, some details about high privileged services are only available with
high privileged user account.

The current version of ospd-netstat does not use such details.
It only retrieves IPv4 TCP ports that are bound to 0.0.0.0.

Optionally, the raw output table of netstat can be dumped into a log file.
This will show all detected ports in the dump.
"""

OSPD_PARAMS = {
    'dumptable': {
        'type': 'boolean',
        'name': 'Dump the output table of netstat',
        'default': 0,
        'mandatory': 0,
        'description': 'Whether to create a log result with the raw output table of netstat.',
    },
}


class OSPDnetstat(OSPDaemonSimpleSSH):

    """ Class for ospd-netstat daemon. """

    def __init__(self, certfile, keyfile, cafile):
        """ Initializes the ospd-netstat daemon's internal data. """
        super(OSPDnetstat, self).__init__(certfile=certfile, keyfile=keyfile,
                                          cafile=cafile)
        self.server_version = __version__
        self.scanner_info['name'] = 'netstat'
        self.scanner_info['version'] = 'depends on the local installation at the target host'
        self.scanner_info['description'] = OSPD_DESC
        for name, param in OSPD_PARAMS.items():
            self.add_scanner_param(name, param)

    def check(self):
        """ Checks that netstat command line tool is found and is executable. """

        # Since the tool is used on each target host, there is no single point of
        # availability. Thus always return true even if on some hosts the tool might be missing.

        return True

    def exec_scan(self, scan_id, target):
        """ Starts the netstat scanner for scan_id scan. """

        options = self.get_scan_options(scan_id)
        dump = options.get('dumptable')

        result = self.run_command(scan_id=scan_id, host=target, cmd="netstat -tlpn")

        if result is None:
            self.add_scan_error(scan_id, host=target,
                                value="A problem occurred trying to execute 'netstat'.")
            self.add_scan_error(scan_id, host=target,
                                value="The result of 'netstat' was empty.")
            return 2

        # initialize the port list
        tcp_ports = []

        # parse the output of the netstat command
        for line in result:
            words = ' '.join(line.split()).split()
            if len(words) > 2 and words[0] == "tcp":
                port = words[3].split(":")[1]
                if words[3].split(":")[0] == '0.0.0.0':
                    tcp_ports.append(port)

        # Create a general log entry about executing netstat
        # It is important to send at least one result, else
        # the host details won't be stored.
        self.add_scan_log(scan_id, host=target, name='Netstat summary',
                          value='Via Netstat %d open tcp ports were found that are bound to local address 0.0.0.0.' % len(tcp_ports))

        # Create a log entry for each found port
        for port in tcp_ports:
            self.add_scan_log(scan_id, host=target, name='Netstat port',
                              port='{0}/tcp'.format(port))

        # If "dump" was set to True, then create a log entry with the dump.
        if dump is 1:
            self.add_scan_log(scan_id, host=target, name='Netstat dump',
                              value='Raw netstat output:\n\n%s' % ''.join(result))

        # store the found ports as host details
        if len(tcp_ports) > 0:
            self.add_scan_host_detail(scan_id, host=target, name="ports",
                                      value=", ".join(tcp_ports))
            self.add_scan_host_detail(scan_id, host=target, name="tcp_ports",
                                      value=", ".join(tcp_ports))
        return 1


def main():
    """ OSP netstat main function. """
    daemon_main('OSPD - netstat wrapper', OSPDnetstat)
