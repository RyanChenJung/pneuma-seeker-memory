import unittest
from unittest.mock import MagicMock

from pneuma_seeker.core.ir_system.main import IRSystem


class TestLMInterface(unittest.TestCase):
    def setUp(self):
        self.lm_interface = IRSystem()
    
    def test_retrieve(self):
        pass
