#!/usr/bin/env python3
import unittest

from rest.environment.environment import EnvironmentSingleton


class RenderTestCase(unittest.TestCase):

    def test_load_env_empty_virt_env(self):
        env = EnvironmentSingleton.get_instance()
        self.assertGreater(len(env.get_env()), 0)
        # self.assertEqual(len(env.get_virtual_env()), 0)

    def test_load_env_var_in_virt_env_single(self):
        env = EnvironmentSingleton.get_instance()
        is_set = env.set_env_var("FOO1", "v1")
        self.assertEqual(len(env.get_virtual_env()), 1)
        self.assertEqual(is_set, True)
        self.assertGreater(len(env.get_env()), 0)

    def test_load_env_var_in_virt_env_single_empty_key(self):
        env = EnvironmentSingleton.get_instance()
        is_set = env.set_env_var("", "v1")
        self.assertEqual(is_set, False)
        self.assertGreater(len(env.get_env()), 0)

    def test_load_env_var_in_virt_env_single_override(self):
        env = EnvironmentSingleton.get_instance()
        env.set_env_var("FOO1", "v1")
        is_set = env.set_env_var("FOO1", "v2")
        self.assertEqual(len(env.get_virtual_env()), 1)
        self.assertEqual(env.get_virtual_env(), {"FOO1": "v2"})
        self.assertEqual(is_set, True)
        self.assertGreater(len(env.get_env()), 0)

    def test_load_env_var_in_virt_env_multiple(self):
        env = EnvironmentSingleton.get_instance()
        env_vars_set = env.set_env_vars({"FOO1": "v1"})
        self.assertEqual(len(env.get_virtual_env()), 1)
        self.assertEqual(env.get_virtual_env(), env_vars_set)
        self.assertGreater(len(env.get_env()), 0)

    def test_load_env_var_in_virt_env_multiple_override(self):
        env = EnvironmentSingleton.get_instance()
        env.set_env_vars({"FOO1": "v1"})
        env_vars_set = env.set_env_vars({"FOO1": "v2"})
        self.assertEqual(len(env.get_virtual_env()), 1)
        self.assertEqual(env.get_virtual_env(), env_vars_set)
        self.assertGreater(len(env.get_env()), 0)

    def test_load_env_var_in_virt_env_empty_key_in_dict(self):
        env = EnvironmentSingleton.get_instance()
        env_vars_set = env.set_env_vars({"": "v2"})
        self.assertEqual(env_vars_set, {})
        self.assertGreater(len(env.get_env()), 0)

    def test_maxcap_for_virt_env(self):
        env = EnvironmentSingleton.get_instance()
        env.set_env_vars({"FOO1": "v1"})
        max_cap = EnvironmentSingleton.VIRTUAL_ENV_MAX_SIZE
        for i in range(0, 2 * EnvironmentSingleton.VIRTUAL_ENV_MAX_SIZE):
            is_set = env.set_env_var(f"{i}", f"{i}")
        self.assertEqual(is_set, False)
        self.assertEqual(len(env.get_virtual_env()), EnvironmentSingleton.VIRTUAL_ENV_MAX_SIZE)
        self.assertEqual(env.get_virtual_env().get(EnvironmentSingleton.VIRTUAL_ENV_MAX_SIZE), None)
        self.assertGreater(len(env.get_env()), 0)


if __name__ == '__main__':
    unittest.main()
