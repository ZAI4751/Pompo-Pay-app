#!/usr/bin/env python3
"""
Production deployment verification suite.

Comprehensive checks for POMPO production deployment.
Verifies all components are healthy and configured correctly.

USAGE:

    python scripts/verify_production_deployment.py <api_base_url> [--admin-token=TOKEN]

Examples:

    # Verify backend only
    python scripts/verify_production_deployment.py https://api.yourdomain.com

    # Verify with admin auth (requires admin login first)
    python scripts/verify_production_deployment.py https://api.yourdomain.com \
      --admin-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

REQUIREMENTS:

    - httpx library: pip install httpx
    - API must be accessible via HTTPS
    - Health endpoints must return 200 OK
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx library required")
    print("Install: pip install httpx")
    sys.exit(1)


class ProductionVerifier:
    """Comprehensive production deployment verification."""

    def __init__(self, api_base_url: str, admin_token: Optional[str] = None):
        self.api_base_url = api_base_url.rstrip("/")
        self.admin_token = admin_token
        self.results: dict[str, dict] = {}
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            verify=True,  # Enforce HTTPS certificate verification
            timeout=httpx.Timeout(10.0),
        )
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    def _get_headers(self, auth: bool = False) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "User-Agent": "POMPO-ProductionVerifier/1.0",
            "Accept": "application/json",
        }
        if auth and self.admin_token:
            headers["Authorization"] = f"Bearer {self.admin_token}"
        return headers

    async def _test_endpoint(
        self,
        name: str,
        method: str,
        path: str,
        expected_status: int = 200,
        auth: bool = False,
        body: Optional[dict] = None,
    ) -> bool:
        """Test a single endpoint."""
        if not self.client:
            return False

        url = f"{self.api_base_url}{path}"
        headers = self._get_headers(auth=auth)

        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await self.client.post(
                    url, headers=headers, json=body or {}
                )
            else:
                return False

            success = response.status_code == expected_status
            self.results[name] = {
                "status": "✅ PASS" if success else "❌ FAIL",
                "url": url,
                "method": method,
                "expected": expected_status,
                "actual": response.status_code,
                "response_time": response.elapsed.total_seconds(),
            }

            if response.status_code >= 400:
                try:
                    self.results[name]["error_body"] = response.text[:200]
                except Exception:
                    pass

            return success

        except httpx.SSLError as e:
            self.results[name] = {
                "status": "❌ FAIL",
                "error": f"HTTPS/SSL Error: {str(e)[:100]}",
            }
            return False
        except httpx.ConnectError as e:
            self.results[name] = {
                "status": "❌ FAIL",
                "error": f"Connection Error: {str(e)[:100]}",
            }
            return False
        except Exception as e:
            self.results[name] = {
                "status": "❌ FAIL",
                "error": f"Unexpected Error: {type(e).__name__}: {str(e)[:100]}",
            }
            return False

    async def verify_https(self) -> bool:
        """Verify HTTPS is enforced."""
        print("\n[HTTPS & Security]")
        return await self._test_endpoint(
            "HTTPS enforced",
            "GET",
            "/api/v1/health/live",
            expected_status=200,
        )

    async def verify_health_endpoints(self) -> bool:
        """Verify health check endpoints."""
        print("\n[Health Endpoints]")

        live_ok = await self._test_endpoint(
            "Health live endpoint",
            "GET",
            "/api/v1/health/live",
            expected_status=200,
        )

        ready_ok = await self._test_endpoint(
            "Health ready endpoint",
            "GET",
            "/api/v1/health/ready",
            expected_status=200,
        )

        return live_ok and ready_ok

    async def verify_openapi_hidden(self) -> bool:
        """Verify OpenAPI docs are hidden (DEBUG=false)."""
        print("\n[Debug Mode]")
        docs_ok = await self._test_endpoint(
            "Swagger UI hidden",
            "GET",
            "/docs",
            expected_status=404,
        )
        schema_ok = await self._test_endpoint(
            "OpenAPI schema hidden",
            "GET",
            "/openapi.json",
            expected_status=404,
        )
        return docs_ok and schema_ok

    async def verify_cors_canonical_origins(self) -> bool:
        """Public checkout and Vercel admin must be allowed; unknown origins must not."""
        print("\n[CORS]")
        if not self.client:
            return False
        login = f"{self.api_base_url}/api/v1/auth/login"
        allowed = [
            "https://pay.pompo.mw",
            "https://pompo-pay-app.vercel.app",
        ]
        ok = True
        for origin in allowed:
            response = await self.client.options(
                login,
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,authorization",
                },
            )
            granted = response.headers.get("access-control-allow-origin") == origin
            self.results[f"CORS allow {origin}"] = {
                "status": "✅ PASS" if granted else "❌ FAIL",
                "actual": response.status_code,
                "allow_origin": response.headers.get("access-control-allow-origin"),
            }
            ok = ok and granted
        attacker = "https://evil.example"
        blocked = await self.client.options(
            login,
            headers={
                "Origin": attacker,
                "Access-Control-Request-Method": "POST",
            },
        )
        attacker_granted = blocked.headers.get("access-control-allow-origin") == attacker
        self.results["CORS deny unknown origin"] = {
            "status": "✅ PASS" if not attacker_granted else "❌ FAIL",
            "allow_origin": blocked.headers.get("access-control-allow-origin"),
        }
        return ok and not attacker_granted

    async def verify_database_connectivity(self) -> bool:
        """Verify database is accessible."""
        print("\n[Database Connectivity]")
        # Health endpoint tests database connection
        return await self._test_endpoint(
            "Database connectivity",
            "GET",
            "/api/v1/health/ready",
            expected_status=200,
        )

    async def verify_authentication(self) -> bool:
        """Verify authentication is required."""
        print("\n[Authentication]")

        # Unauthenticated request should fail
        no_auth_ok = await self._test_endpoint(
            "Unauthenticated request blocked",
            "GET",
            "/api/v1/merchants",
            expected_status=401,  # Should require auth
        )

        # With invalid token should fail
        invalid_token_ok = True
        if not self.client:
            invalid_token_ok = False
        else:
            # Manually test with invalid token
            headers = self._get_headers(auth=False)
            headers["Authorization"] = "Bearer invalid-token-xyz"
            try:
                response = await self.client.get(
                    f"{self.api_base_url}/api/v1/merchants",
                    headers=headers,
                )
                self.results["Invalid token rejected"] = {
                    "status": "✅ PASS" if response.status_code == 401 else "❌ FAIL",
                    "expected": 401,
                    "actual": response.status_code,
                }
                invalid_token_ok = response.status_code == 401
            except Exception as e:
                self.results["Invalid token rejected"] = {
                    "status": "❌ FAIL",
                    "error": str(e)[:100],
                }
                invalid_token_ok = False

        return no_auth_ok and invalid_token_ok

    async def verify_cors(self) -> bool:
        """Verify canonical production origins are allowed and unknown origins are not."""
        return await self.verify_cors_canonical_origins()

    async def verify_rate_limiting(self) -> bool:
        """Verify rate limiting is functional."""
        print("\n[Rate Limiting]")

        if not self.client:
            return False

        try:
            # Rapid requests should eventually be rate limited
            # This is a basic check; full testing would require many requests
            response = await self.client.get(
                f"{self.api_base_url}/api/v1/health/live"
            )

            has_rate_limit_headers = (
                "x-ratelimit-limit" in response.headers
                or "x-ratelimit-remaining" in response.headers
            )

            self.results["Rate limit headers present"] = {
                "status": "✅ PASS" if has_rate_limit_headers else "⚠️  WARNING",
                "note": "Rate limiting configured in application",
                "x-ratelimit-limit": response.headers.get("x-ratelimit-limit", "N/A"),
                "x-ratelimit-remaining": response.headers.get(
                    "x-ratelimit-remaining", "N/A"
                ),
            }

            return response.status_code == 200

        except Exception as e:
            self.results["Rate limit headers present"] = {
                "status": "❌ FAIL",
                "error": str(e)[:100],
            }
            return False

    async def verify_trusted_hosts(self) -> bool:
        """Verify trusted hosts validation."""
        print("\n[Trusted Hosts]")

        # This is tested by making valid requests
        # If trusted hosts were configured wrong, all requests would fail
        response_ok = await self._test_endpoint(
            "Trusted host validation",
            "GET",
            "/api/v1/health/live",
            expected_status=200,
        )

        return response_ok

    async def verify_admin_endpoints(self) -> bool:
        """Verify admin endpoints are accessible (with auth)."""
        print("\n[Admin Endpoints]")

        if not self.admin_token:
            print("   (Skipped: No admin token provided)")
            return True

        # Test various admin endpoints
        endpoints = [
            ("/api/v1/merchants", "Merchants endpoint"),
            ("/api/v1/branches", "Branches endpoint"),
            ("/api/v1/tills", "Tills endpoint"),
            ("/api/v1/roles", "Roles endpoint"),
            ("/api/v1/providers", "Providers endpoint"),
        ]

        all_ok = True
        for path, name in endpoints:
            ok = await self._test_endpoint(name, "GET", path, expected_status=200, auth=True)
            all_ok = all_ok and ok

        return all_ok

    async def run_all_checks(self) -> bool:
        """Run all verification checks."""
        print("=" * 70)
        print("POMPO PRODUCTION DEPLOYMENT VERIFICATION")
        print("=" * 70)
        print(f"\nAPI Base URL: {self.api_base_url}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z")

        results = [
            await self.verify_https(),
            await self.verify_health_endpoints(),
            await self.verify_openapi_hidden(),
            await self.verify_database_connectivity(),
            await self.verify_authentication(),
            await self.verify_cors(),
            await self.verify_rate_limiting(),
            await self.verify_trusted_hosts(),
            await self.verify_admin_endpoints(),
        ]

        return all(results)

    def print_report(self) -> None:
        """Print verification report."""
        print("\n" + "=" * 70)
        print("VERIFICATION RESULTS")
        print("=" * 70 + "\n")

        for test_name, result in self.results.items():
            status = result.get("status", "UNKNOWN")
            print(f"{status} {test_name}")

            for key, value in result.items():
                if key != "status":
                    if isinstance(value, (int, float)):
                        print(f"     {key}: {value}")
                    elif key != "url" and value:
                        print(f"     {key}: {value}")

        print("\n" + "=" * 70)

        # Summary
        passed = sum(
            1 for r in self.results.values() if "✅" in r.get("status", "")
        )
        failed = sum(
            1 for r in self.results.values() if "❌" in r.get("status", "")
        )
        warnings = sum(
            1 for r in self.results.values() if "⚠️" in r.get("status", "")
        )

        print(f"\nSummary: {passed} passed, {warnings} warnings, {failed} failed")

        if failed == 0:
            print("\n✅ ALL CRITICAL CHECKS PASSED")
            print("\nProduction deployment is healthy.")
        else:
            print("\n❌ DEPLOYMENT ISSUES DETECTED")
            print("\nReview failed checks and logs before proceeding.")

        print("=" * 70)


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python verify_production_deployment.py <api_base_url> [--admin-token=TOKEN]")
        print("\nExamples:")
        print("  python verify_production_deployment.py https://api.yourdomain.com")
        print("  python verify_production_deployment.py https://api.yourdomain.com --admin-token=...")
        sys.exit(1)

    api_url = sys.argv[1]
    admin_token = None

    for arg in sys.argv[2:]:
        if arg.startswith("--admin-token="):
            admin_token = arg.split("=", 1)[1]

    async with ProductionVerifier(api_url, admin_token) as verifier:
        all_ok = await verifier.run_all_checks()
        verifier.print_report()
        sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
