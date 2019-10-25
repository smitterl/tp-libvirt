import unittest
import os

try:
    from unittest import mock
except ImportError:
    import mock

from libvirt.tests.src import smt
from virttest.cartesian_config import Parser

CPU_INFO = """
CPU(s):              8
Thread(s) per core:  %s
Core(s) per socket:  %s
Socket(s):           1
"""


@mock.patch('time.sleep')
@mock.patch.object(smt, 'to_text', return_value="Threads per core: 2")
@mock.patch.object(smt.process, 'system_output')
@mock.patch.object(smt.vm_xml.VMXML, 'new_from_inactive_dumpxml')
@mock.patch.object(smt.utils_package, 'package_install')
class TestSmt(unittest.TestCase):
    """
    Sample tests cases for smt.py
    """

    env = None
    test = None
    params = None
    vm = None

    def setUp(self):
        self.env = mock.MagicMock()
        self.test = mock.MagicMock()
        self.test.fail = mock.MagicMock(side_effect=Exception())
        self.params = get_test_params(get_cfg(smt), 'smt.positive.smt8')

        self.vm = mock.MagicMock()
        self.env.get_vm = mock.MagicMock(return_value=self.vm)
        self.session = mock.MagicMock()
        self.vm.wait_for_login = mock.MagicMock(return_value=self.session)

        # The test modifies guest system properties several times and checks
        # cmd output. This list represents the ordered sequence of expected output
        # for the specific case 'smt.positive.smt8'
        self.session.cmd_output = mock.Mock(side_effect=[
            (CPU_INFO % (8, 4)),
            "SMT=8", "0",
            "0",
            "SMT is off", "0",
            "Number of cores present = 4", "0",
            "Number of cores online = 4", "0",
            "Threads per core: 8", "0",
            "", "0",
            "Number of cores online = 3", "0",
            (CPU_INFO % (1, 3)),
            "", "0",
            "Number of cores online = 2", "0",
            (CPU_INFO % (1, 2)),
        ])

    def test_smt_positive_smt8_passes(self, *mocks):
        smt.run(self.test, self.params, self.env)

    def test_smt_positive_smt8_installs_package_when_no_error(self, *mocks):
        smt.run(self.test, self.params, self.env)
        smt.utils_package.package_install.assert_called_once()

    def test_smt_positive_smt8_status_error_must_be_no(self, *mocks):
        self.params["status_error"] = "yes"
        with self.assertRaises(Exception):
            smt.run(self.test, self.params, self.env)
        smt.utils_package.package_install.assert_not_called()


class TestHelpers(unittest.TestCase):
    """
    Test cases for the configuration helper methods
    """

    def test_get_cfg(self):
        cfg = get_cfg(smt)
        self.assertTrue(cfg.endswith("libvirt/tests/cfg/smt.cfg"))

    def test_get_test_params(self):
        params = get_test_params(get_cfg(smt), 'smt.positive.smt1')
        self.assertIsNotNone(params.get("status_error"))
        self.assertEqual(params.get("type"), "smt")


def get_cfg(test_module):
    """
    Returns the test configuration that contains the test parameters
    :param test_module: The imported name of the test script
    :return: The absolute path to the test configuration
    """
    tst_py_path = os.path.abspath(test_module.__file__)
    return tst_py_path.replace('src', 'cfg').replace('.py', '.cfg')


def get_test_params(cfg, test_name):
    """
    Returns all test parameters that are set in the configuration file
    ignoring any higher level test parameters, e.g. from base.cfg
    :param cfg: The absolute path to the test configuration file
    :param test_name: The test name that is used by the avocado-vt plugin
    :return: The params dictionary for run(test, params, env)
    """
    with open(cfg, 'r') as c:
        cfg_s = "variants:\n"
        line = c.readline()
        while line:
            # remove any filter for get_dict to generate params independently of
            # parent cfg
            if line.strip().startswith("only") or line.strip().startswith("no"):
                line = c.readline()
                continue
            else:
                cfg_s += line + "\n"
                line = c.readline()

    parser = Parser()
    parser.parse_string(cfg_s)
    for params in (_ for _ in parser.get_dicts()):
        if params['shortname'] == test_name:
            return params
    return None


if __name__ == '__main__':
    unittest.main()
