"""
This module provides helper functions used with the
vfio_ccw passthrough driver on s390x.
"""

import logging

from avocado.core.exceptions import TestError

from virttest import utils_package
from virttest import virsh
from virttest.utils_zchannels import SubchannelPaths
from virttest.utils_misc import cmd_status_output
from virttest.libvirt_xml.devices.hostdev import Hostdev


def device_is_listed(session, chpids):
    """
    Checks if the css device is listed by comparing the channel
    path ids.

    :param session: guest console session
    :param chipds: chpids where the disk is connected, e.g. "11122122"
    """

    paths = SubchannelPaths(session)
    paths.get_info()
    devices_inside_guest = [x for x in paths.devices
                            if x[paths.HEADER["CHPIDs"]] == chpids]
    return len(devices_inside_guest) > 0


def set_override(schid):
    """
    Sets the driver override for the device' subchannel.

    :param schid: Subchannel path id for device.
    """

    cmd = "driverctl -b css set-override %s vfio_ccw" % schid
    err, out = cmd_status_output(cmd, shell=True)
    if err:
        raise TestError("Can't set driver override. %s" % out)


def unset_override(schid):
    """
    Unsets the driver override for the device' subchannel.

    :param schid: Subchannel path id for device.
    """

    cmd = "driverctl -b css unset-override %s" % schid
    err, out = cmd_status_output(cmd, shell=True)
    if err:
        raise TestError("Can't set driver override. %s" % out)


def start_device(uuid, schid):
    """
    Starts the mdev with mdevctl

    :param uuid: device uuid
    :param schid: subchannel id for the device
    """

    cmd = "mdevctl start -u %s -p %s -t vfio_ccw-io" % (uuid, schid)
    err, out = cmd_status_output(cmd, shell=True)
    if err:
        raise TestError("Can't start mdev. %s" % out)


def stop_device(uuid):
    """
    Stops the mdev with mdevctl

    :param uuid: device uuid
    """

    cmd = "mdevctl stop -u %s" % (uuid)
    err, out = cmd_status_output(cmd, shell=True)
    if err:
        logging.warning("Couldn't stop device. %s", out)


def attach_hostdev(vm_name, uuid):
    """
    Attaches the mdev to the machine.

    :param vm_name: VM name
    :param uuid: mdev uuid
    """

    hostdev_xml = Hostdev()
    hostdev_xml.mode = "subsystem"
    hostdev_xml.model = "vfio-ccw"
    hostdev_xml.type = "mdev"
    hostdev_xml.source = hostdev_xml.new_source(**{"uuid": uuid})
    hostdev_xml.xmltreefile.write()
    virsh.attach_device(vm_name, hostdev_xml.xml, flagstr="--current",
                        ignore_status=False)


def assure_preconditions():
    """
    Makes sure that preconditions are established.
    """

    utils_package.package_install("mdevctl")
    utils_package.package_install("driverctl")


def get_device_info():
    """
    Gets the device info for passthrough
    """

    paths = SubchannelPaths()
    paths.get_info()
    device = paths.get_first_unused_and_safely_removable()
    schid = device[paths.HEADER["Subchan."]]
    chpids = device[paths.HEADER["CHPIDs"]]
    return schid, chpids
