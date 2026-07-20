"""Service layer — domain logic the HTTP routes delegate to.

Keeping the logic out of the route handlers makes it unit-testable (the
provisioning tests exercise these functions through the HTTP layer, but the
tenant-isolation + device state-machine rules are pure functions here).
"""
