"""The register validates its immutable BOQ baseline and controlled states in service.py.

Rules are enforced during every write, including imports; there is deliberately
no second approval workflow or separate commercial-quantity validator here.
"""
