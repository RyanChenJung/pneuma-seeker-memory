"""Walking-skeleton tests (Goal WS) — knowledge injection wired into Pneuma, flag-gated.

Success criteria proven here:
- T3 maps a known persona, returns None for unknown.
- T4 loads the authored knowledge for a department.
- The injector composes the right SYSTEM text for a known persona, None otherwise.
- The flag defaults OFF (baseline) and the conductor hook only injects when ON.
- Flag OFF (or unknown persona) leaves `llm_messages` untouched == baseline.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from pneuma_seeker.services.memory import MemoryInjector
from pneuma_seeker.services.memory.t3_identity import UserIdentity
from pneuma_seeker.services.memory.t4_authored import AuthoredKnowledge
from pneuma_seeker.shared.config import Config
from pneuma_seeker.shared.schemas.language_model.role import Role

# The conductor pulls in the full Pneuma runtime (duckdb / chromadb / ...). When that stack
# is not installed (e.g. this lean dev box) the SC-2 wiring test skips gracefully; it runs in
# the real Pneuma environment / CI.
try:
    import pneuma_seeker.services.core.conductor.main as conductor_main
    _CONDUCTOR_IMPORTABLE = True
except Exception:  # noqa: BLE001 - any missing runtime dep means "skip", not "fail"
    conductor_main = None
    _CONDUCTOR_IMPORTABLE = False


class T3IdentityTests(unittest.TestCase):
    def test_known_persona(self):
        self.assertEqual(UserIdentity().lookup("u_adm_analyst"), ("Admissions", "analyst"))
        self.assertEqual(UserIdentity().lookup("u_fin_director"), ("Finance", "director"))

    def test_unknown_returns_none(self):
        self.assertIsNone(UserIdentity().lookup("default_user"))
        self.assertIsNone(UserIdentity().lookup("nobody"))


class T4AuthoredTests(unittest.TestCase):
    def test_dept_knowledge_shape(self):
        entries = AuthoredKnowledge().get_dept_knowledge("Admissions")
        self.assertEqual({e["term"] for e in entries}, {"retention", "yield"})
        for e in entries:
            for key in ("definition", "formula", "target_tables", "hidden_rule"):
                self.assertIn(key, e)

    def test_dept_match_is_case_insensitive(self):
        self.assertTrue(AuthoredKnowledge().get_dept_knowledge("finance"))


class InjectorTests(unittest.TestCase):
    def test_known_persona_injects_dept_and_rule(self):
        out = MemoryInjector().get_injection("u_fin_analyst", "what is our retention rate?")
        self.assertIsNotNone(out)
        self.assertIn("Finance", out)
        # Finance retention's hidden rule (schema-invisible) must surface.
        self.assertIn("fiscal year", out.lower())

    def test_same_query_different_persona_different_dept(self):
        q = "what is our retention rate?"
        adm = MemoryInjector().get_injection("u_adm_analyst", q)
        fin = MemoryInjector().get_injection("u_fin_analyst", q)
        self.assertIn("Admissions", adm)
        self.assertIn("Finance", fin)
        self.assertNotEqual(adm, fin)

    def test_unknown_persona_no_injection(self):
        self.assertIsNone(MemoryInjector().get_injection("default_user", "q"))


class ConfigFlagTests(unittest.TestCase):
    def test_default_off(self):
        self.assertFalse(Config().ENABLE_MEMORY_INJECTION)


@unittest.skipUnless(_CONDUCTOR_IMPORTABLE, "full Pneuma runtime not installed")
class ConductorHookTests(unittest.TestCase):
    """Verify the 🟡 SC-2 wiring without running the LLM loop."""

    def _make_conductor(self, flag: bool):
        cm = conductor_main
        config = Config()
        config.ENABLE_MEMORY_INJECTION = flag
        with patch.object(cm, "ActionSet", MagicMock()), patch.object(
            cm, "Materializer", MagicMock()
        ), patch.object(cm, "TableReader", MagicMock()), patch.object(
            cm, "ConductorPromptFactory", MagicMock()
        ):
            return cm.Conductor(
                "u_adm_analyst", "c1", config, MagicMock(),
                MagicMock(), MagicMock(), MagicMock(),
            )

    def test_flag_on_appends_system_message(self):
        c = self._make_conductor(flag=True)
        self.assertIsNotNone(c.memory_injector)
        c.llm_messages = [{"role": Role.SYSTEM.value, "content": "sys"}]
        c._inject_memory("what is our retention rate?")
        self.assertEqual(len(c.llm_messages), 2)
        self.assertEqual(c.llm_messages[1]["role"], "system")
        self.assertIn("Admissions", c.llm_messages[1]["content"])

    def test_flag_off_is_inert(self):
        c = self._make_conductor(flag=False)
        self.assertIsNone(c.memory_injector)
        c.llm_messages = [{"role": "system", "content": "sys"}]
        c._inject_memory("what is our retention rate?")
        self.assertEqual(len(c.llm_messages), 1)  # untouched == baseline

    def test_flag_on_unknown_persona_is_inert(self):
        c = self._make_conductor(flag=True)
        c.user_id = "default_user"  # unknown persona
        c.llm_messages = [{"role": "system", "content": "sys"}]
        c._inject_memory("q")
        self.assertEqual(len(c.llm_messages), 1)


if __name__ == "__main__":
    unittest.main()
