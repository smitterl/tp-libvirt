import logging
import time

from avocado.core.exceptions import TestFail
from virttest.libvirt_xml.vm_xml import VMXML
from virttest.utils_misc import cmd_status_output, wait_for


DEACTIVATE_FORWARDING = 0
FORWARD_COUNTER_TIMEOUT = 360
CHECK_INTERVAL = 60


def update_kvm_parameter(hz):
    """
    Updates kvm paramter for forwarding

    :param hz: diag9c_forwarding_hz
    """

    cmd = "echo %s > /sys/module/kvm/parameters/diag9c_forwarding_hz" % hz
    err, out = cmd_status_output(cmd, shell=True)
    if err:
        raise OSError("Could not update parameter. %s" % out)


def start_locktorture(session):
    """
    Starts spin lock torture test to cause spinlocks in guest

    :param session: guest session
    """
    logging.debug("session is %s" % session)
    cmd = "modprobe locktorture torture_type=spin_lock"
    err, out = cmd_status_output(cmd, shell=True, session=session)
    if err:
        raise OSError("Could not start locktorture. %s" % out)


def confirm_forwarding(hz):
    """
    Confirm if forwarding is happening or not depending on set
    hz parameter

    :param hz: if 0 expect no forwarding, if positive expect forward
    """

    if int(hz) > 0:
        wait_for_forward_count_to_be_non_zero(FORWARD_COUNTER_TIMEOUT)
    else:
        confirm_forward_count_is_still_zero_after(CHECK_INTERVAL)


def confirm_forward_count_is_still_zero_after(interval):
    """
    Wait for a certain time interval and then confirm
    that the counter didn't go up
    """
    time.sleep(interval)
    err, out = get_forward_value()
    if err or int(out) != 0:
        raise TestFail("Counter wasn't zero although forward"
                       " was inactive. Value is %s" % out)
    

def get_forward_value():
    """
    Reads sysfs for forward value
    """
    cmd = "cat /sys/kernel/debug/kvm/diag_9c_forward"
    return cmd_status_output(cmd, shell=True)


def wait_for_forward_count_to_be_non_zero(timeout):
    """
    Wait for the forward counter to become > 0. Fail if it doesn't
    after timeout.
    
    :param timeout: maximum time to wait for counter to go up
    """

    def count_is_non_zero():
        """ Confirm if the count is non-zero """
        err, out = get_forward_value()
        if err:
            return False
        elif int(out) <= 0:
            return False
        elif int(out) > 0:
            return True

    is_non_zero = wait_for(count_is_non_zero, step=10, timeout=timeout)
    if not is_non_zero:
        raise TestFail("Counter didn't go up though forwarding active.")


def run(test, params, env):
    """
    Test if Spinlock Yield Forwarding works
 
    :param test: test object
    :param params: Dict with the test parameters
    :param env: Dict with the test environment
    :return:
    """

    diag9c_forward_hz = params.get("diag9c_forward_hz")
    vm_name = params.get("main_vm")
    vm = env.get_vm(vm_name)
    vmxml = VMXML.new_from_inactive_dumpxml(vm_name)
    vmxml_backup = vmxml.copy()

    try:
        update_kvm_parameter(diag9c_forward_hz)
        session = vm.wait_for_login()
        start_locktorture(session)
        confirm_forwarding(diag9c_forward_hz)
    finally:
        update_kvm_parameter(DEACTIVATE_FORWARDING)
        vmxml_backup.sync()
