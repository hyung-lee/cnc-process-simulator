import unittest
from streamlit.testing.v1 import AppTest
from simulation import simulate,optimize
class Tests(unittest.TestCase):
    def test_consistency(self):
        c=simulate(4200,1000,1.8,35)
        self.assertAlmostEqual(c['defect_pct']+c['yield_pct'],100)
        self.assertAlmostEqual(c['energy_kwh'],c['power_kw']*c['cycle_sec']/3600)
        self.assertEqual(c,simulate(4200,1000,1.8,35))
        self.assertGreater(simulate(4200,1400,1.8,35)['defect_pct'],c['defect_pct'])
        self.assertGreater(simulate(4200,1000,1.8,80)['defect_pct'],c['defect_pct'])
    def test_constraints_and_objectives(self):
        c=simulate(4200,1000,1.8,35)
        for obj in ['균형','전력 절감 우선','양품률 우선']:
            b,d=optimize(c,1.6,95,15,obj)
            self.assertIsNotNone(b)
            self.assertGreaterEqual(b['yield_pct'],95)
            self.assertLessEqual(b['ra'],1.6)
            self.assertLessEqual(b['cycle_sec'],c['cycle_sec']*1.15+1e-9)
            self.assertEqual(b['wear'],35)
            if obj=='전력 절감 우선':self.assertEqual(b['energy_kwh'],d.loc[d.feasible,'energy_kwh'].min())
        self.assertIsNone(optimize(c,1.6,100,15,'균형')[0])
    def test_ui(self):
        at=AppTest.from_file('app.py').run(timeout=30)
        self.assertFalse(at.exception)
        self.assertEqual(len(at.metric),0)
        at.button[0].click().run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(any('예상 양품률'==m.label for m in at.metric))
        at.number_input(key='min_yield').set_value(100.)
        at.button[0].click().run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(any('후보가 없습니다' in x.value for x in at.warning))
if __name__=='__main__':unittest.main()
