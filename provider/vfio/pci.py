from virttest.libvirt_xml.nodedev_xml import NodedevXML
from virttest import virsh

def get_nodedev(driver_name):
    ret = virsh.nodedev_list(cap="pci")
    for name in ret.stdout.split():
        pci_xml = NodedevXML.new_from_dumpxml(name)
        if pci_xml.driver_name == driver_name:
            return pci_xml
