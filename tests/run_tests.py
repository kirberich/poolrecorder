#!/usr/bin/env python
import unittest
from unittest import TestLoader, TextTestRunner
import sys

sys.path.append('../')

TEST_PATH = "."

loader = TestLoader()
runner = TextTestRunner()

runner.run(loader.discover(TEST_PATH))