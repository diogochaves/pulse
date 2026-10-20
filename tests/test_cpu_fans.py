import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'collectors' / 'cpu_pulse.py'
spec = importlib.util.spec_from_file_location('cpu_pulse', SOURCE)
cpu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpu)


def chip(root, index, name, files):
    h = root / f'hwmon{index}'
    h.mkdir()
    (h / 'name').write_text(name + '\n')
    for file, value in files.items():
        (h / file).write_text(f'{value}\n')


class FanTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patcher = patch.object(cpu, 'HWMON', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_board_fans_with_duty(self):
        # nct6683 on an MSI X870E: CPU fan spinning, two empty headers, no labels.
        chip(self.root, 0, 'nct6687', {'fan1_input': 2459, 'pwm1': 255, 'fan2_input': 0, 'pwm2': 255,
                                       'fan3_input': 0, 'fan12_input': 960})
        self.assertEqual(cpu.fans(), [
            {'key': 'nct6687/fan1', 'label': 'fan1', 'rpm': 2459, 'duty': 100.0},
            {'key': 'nct6687/fan12', 'label': 'fan12', 'rpm': 960, 'duty': None},
        ])

    def test_a_fan_seen_spinning_stays_when_it_stops(self):
        chip(self.root, 0, 'nct6687', {'fan1_input': 0, 'pwm1': 0, 'fan2_input': 0})
        self.assertEqual(cpu.fans({'nct6687/fan1'}), [{'key': 'nct6687/fan1', 'label': 'fan1', 'rpm': 0, 'duty': 0.0}])

    def test_labels_are_used(self):
        chip(self.root, 0, 'thinkpad', {'fan1_input': 3100, 'fan1_label': 'CPU'})
        self.assertEqual(cpu.fans()[0]['label'], 'CPU')

    def test_gpu_fans_are_left_to_gpu_pulse(self):
        chip(self.root, 0, 'amdgpu', {'fan1_input': 1500, 'pwm1': 100})
        self.assertEqual(cpu.fans(), [])

    def test_no_driver_is_an_empty_list(self):
        chip(self.root, 0, 'k10temp', {'temp1_input': 93000})
        self.assertEqual(cpu.fans(), [])

    def test_out_of_range_duty_is_unknown(self):
        chip(self.root, 0, 'it8689', {'fan1_input': 900, 'pwm1': 300})
        self.assertIsNone(cpu.fans()[0]['duty'])


if __name__ == '__main__':
    unittest.main()
