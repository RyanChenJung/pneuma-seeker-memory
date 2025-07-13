import unittest
from unittest.mock import MagicMock

from processor.core.ir_system.lm_interface import LMInterface


class TestLMInterface(unittest.TestCase):
    def setUp(self):
        self.lm_interface = LMInterface()
    
    def test_retrieve(self):
        pass
