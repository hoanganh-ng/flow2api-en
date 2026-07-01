"""Verify API-mode captcha injects solution user_agent into the request fingerprint.

Background: YesCaptcha / CapMonster / EzCaptcha / CapSolver solutions include
gRecaptchaResponse and userAgent. Google reCAPTCHA V3 evaluation checks that
the token and the User-Agent of the submission request match, so when calling
the Flow API the UA returned by the captcha service must be reused;
otherwise the server flags it as UNUSUAL_ACTIVITY and returns
"reCAPTCHA evaluation failed".
"""

import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from src.services.flow_client import FlowClient


class _FakeProxyManager:
    async def get_request_proxy_url(self):
        return None


class _FakeAsyncSession:
    """Mock curl_cffi's AsyncSession: createTask returns taskId, getTaskResult returns ready."""

    def __init__(self):
        self._calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        self._calls += 1
        response = MagicMock()
        if self._calls == 1:
            # createTask
            response.status_code = 200
            response.json.return_value = {
                "errorId": 0,
                "taskId": "tid-xyz",
            }
        else:
            # getTaskResult
            response.status_code = 200
            response.json.return_value = {
                "errorId": 0,
                "status": "ready",
                "solution": {
                    "gRecaptchaResponse": "token-abc",
                    "userAgent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/147.0.0.0 Safari/537.36"
                    ),
                },
            }
        return response


class ApiCaptchaFingerprintTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_captcha_returns_token_and_user_agent(self):
        """_get_api_captcha_token must return a (token, userAgent) tuple."""
        import contextvars
        flow = FlowClient.__new__(FlowClient)
        flow._request_fingerprint_ctx = contextvars.ContextVar("fingerprint", default=None)
        flow.proxy_manager = _FakeProxyManager()
        fake_session = _FakeAsyncSession()

        with patch("src.services.flow_client.AsyncSession", lambda *a, **kw: fake_session), \
             patch("src.services.flow_client.config") as cfg, \
             patch("asyncio.sleep", new=AsyncMock()):
            cfg.yescaptcha_api_key = "key"
            cfg.yescaptcha_base_url = "https://api.yescaptcha.com"
            cfg.yescaptcha_task_type = "RecaptchaV3TaskProxylessM1"
            cfg.debug_enabled = False

            result = await flow._get_api_captcha_token(
                method="yescaptcha",
                project_id="proj-1",
                action="IMAGE_GENERATION",
            )

        self.assertIsNotNone(result, "Function should not return None because ready state is mocked")
        self.assertIsInstance(result, tuple, "_get_api_captcha_token must return a (token, userAgent) tuple")
        token, user_agent = result
        self.assertEqual(token, "token-abc")
        self.assertIn("Windows", user_agent, "userAgent should come from the captcha service solution and contain Windows")
        self.assertIn("Chrome/147", user_agent)


if __name__ == "__main__":
    unittest.main()