"""Dev-only tooling for Wizard's Cavern (headless playtest harness + report).

These modules drive the game logic without the Toga UI. They live OUTSIDE
the ``wizardscavern`` package on purpose so Briefcase (which bundles only
``sources = ["wizardscavern"]``) does not ship them in the APK.

Run from the repo root:

    python3 -m playtest_tools.playtest_harness --seed 42 --turns 200
"""
