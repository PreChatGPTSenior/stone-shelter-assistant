"""Shared implementation for evaluation tests.

Sibling modules provide model configurations, run identities, artifact writing,
telemetry capture, evidence checks, source restoration and judge rubrics.
Evaluation test entry points stay in the parent package. Importing this package
does not prepare services, execute a workflow or invoke a model.
"""
