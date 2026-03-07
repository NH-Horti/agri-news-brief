import unittest

from schemas import GithubPutRequest, NaverSearchParams, ensure_github_dir_items, ensure_naver_response


class TestSchemas(unittest.TestCase):
    def test_ensure_naver_response_normalizes_items(self):
        out = ensure_naver_response({"items": "not-a-list", "errorCode": "012"})
        self.assertEqual(out["items"], [])
        self.assertEqual(out.get("errorCode"), "012")

    def test_ensure_github_dir_items_filters_non_dict(self):
        out = ensure_github_dir_items([{"name": "a"}, 1, "x", {"name": "b"}])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].get("name"), "a")
        self.assertEqual(out[1].get("name"), "b")

    def test_naver_search_params_normalizes_values(self):
        params = NaverSearchParams(query="q", display=0, start=-1, sort="")
        out = params.to_request_params()
        self.assertEqual(out["query"], "q")
        self.assertEqual(out["display"], 1)
        self.assertEqual(out["start"], 1)
        self.assertEqual(out["sort"], "date")

    def test_github_put_request_to_json(self):
        req = GithubPutRequest(message="m", content_b64="abc", branch="main", sha="sha1")
        out = req.to_request_json()
        self.assertEqual(out["message"], "m")
        self.assertEqual(out["content"], "abc")
        self.assertEqual(out["branch"], "main")
        self.assertEqual(out["sha"], "sha1")


if __name__ == "__main__":
    unittest.main()