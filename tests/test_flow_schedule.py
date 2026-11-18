"""Guard the 23:30 KST flow-only slot without paid API side effects."""
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/update-and-publish.yml'

class FlowScheduleTests(unittest.TestCase):
    def test_late_evening_and_existing_schedules_remain(self):
        text = WORKFLOW.read_text()
        for cron in ('30 14 * * *', '30 22 * * *', '30 11 * * *', '0 7 * * *'):
            self.assertIn("- cron: '" + cron + "'", text)

    def test_2330_only_enables_flow_collection(self):
        self.assertNotIn("30 7 * * *", WORKFLOW.read_text())
        steps = WORKFLOW.read_text().split('      - name: ')[1:]
        enabled = [s.splitlines()[0] for s in steps if "github.event.schedule == '30 14 * * *'" in s]
        self.assertEqual(enabled, [
            'Install free KRX client for end-of-day investor and short data',
            'Collect APR investor, pension, short and KSD lending (free)'])

if __name__ == '__main__':
    unittest.main()
