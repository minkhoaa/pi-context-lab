# Task M: Cross-Service Navigation and Header Contract Alignment

You are working in the `micro_mesh` monorepo fixture under `fixtures/task-m`.

### Objective
An end-to-end checkout transaction initiated at the API Gateway fails when contacting downstream microservices.

1. Execute the integration test suite:
   `python3 test_integration.py`
2. Follow the call path across services:
   - `packages/gateway`
   - `packages/auth_service`
   - `packages/inventory_service`
   - `packages/billing_service`
   - `packages/shared_types`
3. Trace the header contracts between `ApiGateway` and downstream services. Identify the header contract mismatch causing billing rejection.
4. Align the contract and headers so that `test_integration.py` passes completely without breaking any service boundaries.
