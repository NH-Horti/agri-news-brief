"""편집 평가/교체안 호출이 max_output_tokens 에 잘려 JSON 파싱에 실패하면 예산을 늘려 1회 재시도한다."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import editorial_eval


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _usage(out):
    return {"input_tokens": 1000, "output_tokens": out, "total_tokens": 1000 + out}


class _TruncatingSession:
    """첫 응답은 잘린 JSON(status=incomplete), 두 번째는 완전한 JSON."""

    def __init__(self, first_status="incomplete", first_text='{"score": 77, "issues": [{"type": "wrong_sec'):
        self.requests = []
        self.first_status = first_status
        self.first_text = first_text

    def post(self, url, headers=None, json=None, timeout=None):
        self.requests.append(dict(json or {}))
        if len(self.requests) == 1:
            payload = {"model": "m", "usage": _usage(1500), "output_text": self.first_text}
            if self.first_status:
                payload["status"] = self.first_status
                payload["incomplete_details"] = {"reason": "max_output_tokens"}
            return _Resp(payload)
        return _Resp({"model": "m", "usage": _usage(900), "output_text": json_dumps({"score": 77, "issues": []})})


def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


class OutputLimitRetryTests(unittest.TestCase):
    def _call(self, session, budget=2400, cap=8000):
        return editorial_eval._request_structured_json(
            session,
            headers={},
            request_body={"model": "m", "max_output_tokens": budget},
            timeout_sec=10,
            max_output_tokens_cap=cap,
            model_for_usage="m",
        )

    def test_incomplete_response_is_retried_with_a_larger_budget(self):
        session = _TruncatingSession()
        payload, raw, parsed, usage = self._call(session)
        self.assertEqual(parsed["score"], 77)
        self.assertEqual(len(session.requests), 2)
        self.assertEqual(session.requests[0]["max_output_tokens"], 2400)
        self.assertEqual(session.requests[1]["max_output_tokens"], 4800)
        self.assertEqual(usage["output_tokens"], 2400)
        self.assertTrue(usage["retried_after_output_limit"])

    def test_unparsable_text_without_status_is_also_retried(self):
        session = _TruncatingSession(first_status="")
        _payload, _raw, parsed, _usage_ = self._call(session)
        self.assertEqual(parsed["score"], 77)
        self.assertEqual(len(session.requests), 2)

    def test_retry_budget_respects_cap_and_gives_up_once(self):
        class AlwaysTruncated(_TruncatingSession):
            def post(self, url, headers=None, json=None, timeout=None):
                self.requests.append(dict(json or {}))
                return _Resp({"model": "m", "usage": _usage(10), "status": "incomplete",
                              "incomplete_details": {"reason": "max_output_tokens"}, "output_text": '{"score"'})

        session = AlwaysTruncated()
        with self.assertRaises(ValueError):
            self._call(session, budget=2400, cap=3000)
        self.assertEqual([r["max_output_tokens"] for r in session.requests], [2400, 3000])

    def test_clean_response_uses_a_single_call(self):
        class Clean(_TruncatingSession):
            def post(self, url, headers=None, json=None, timeout=None):
                self.requests.append(dict(json or {}))
                return _Resp({"model": "m", "usage": _usage(500), "output_text": json_dumps({"score": 80})})

        session = Clean()
        _payload, _raw, parsed, usage = self._call(session)
        self.assertEqual(parsed["score"], 80)
        self.assertEqual(len(session.requests), 1)
        self.assertNotIn("retried_after_output_limit", usage)


if __name__ == "__main__":
    unittest.main()
