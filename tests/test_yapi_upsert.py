#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Offline unit tests for the yapi-skill write capability (no network).

Run:  python3 tests/test_yapi_upsert.py
Network calls are monkeypatched; these lock the write-safety edges flagged in
the 2026-06-03 Codex review (case-sensitive match, paging fail-closed, multi
match, unknown fields, path-level params, dry-run before/after).
"""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "yapi-skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import openapiToYapiPayload as o2y  # noqa: E402
import upsertInterface as up  # noqa: E402


def fake_config(**kw):
    base = dict(base_url="http://x", project_tokens={"1": "t"}, timeout_seconds=60,
                verify_tls=True, search_page_size=2, search_max_pages=2)
    base.update(kw)
    return types.SimpleNamespace(**base)


class TestNormalizePath(unittest.TestCase):
    def test_case_sensitive(self):
        self.assertNotEqual(common.normalize_api_path("/User"), common.normalize_api_path("/user"))

    def test_trailing_slash_stripped(self):
        self.assertEqual(common.normalize_api_path("/a/b/"), "/a/b")

    def test_root_kept(self):
        self.assertEqual(common.normalize_api_path("/"), "/")

    def test_trim(self):
        self.assertEqual(common.normalize_api_path("  /a  "), "/a")


class TestFindInterface(unittest.TestCase):
    def _patch_pages(self, pages):
        def fake(config, pid, page, limit):
            idx = page - 1
            if idx < len(pages):
                items, total = pages[idx]
                return {"list": items, "total": total}
            return {"list": [], "total": pages[-1][1] if pages else 0}
        common.yapi_list_interfaces_raw = fake

    def test_single_match(self):
        self._patch_pages([([{"_id": 5, "path": "/a", "method": "GET"}], 1)])
        self.assertEqual(common.find_interface_by_path_method(fake_config(), 1, "/a", "get")["_id"], 5)

    def test_method_case_insensitive(self):
        self._patch_pages([([{"_id": 5, "path": "/a", "method": "get"}], 1)])
        self.assertEqual(common.find_interface_by_path_method(fake_config(), 1, "/a", "GET")["_id"], 5)

    def test_no_match_when_fully_scanned(self):
        self._patch_pages([([{"_id": 5, "path": "/b", "method": "GET"}], 1)])
        self.assertIsNone(common.find_interface_by_path_method(fake_config(), 1, "/a", "get"))

    def test_path_case_sensitive_no_false_match(self):
        self._patch_pages([([{"_id": 5, "path": "/User", "method": "GET"}], 1)])
        self.assertIsNone(common.find_interface_by_path_method(fake_config(), 1, "/user", "get"))

    def test_multiple_match_raises(self):
        self._patch_pages([([{"_id": 5, "path": "/a", "method": "GET"},
                             {"_id": 6, "path": "/a", "method": "GET"}], 2)])
        with self.assertRaises(common.YapiSkillError):
            common.find_interface_by_path_method(fake_config(), 1, "/a", "get")

    def test_incomplete_scan_fails_closed(self):
        # total=10 >> max_pages*page_size = 2*2 = 4; not found -> must raise, not return None
        pages = [([{"_id": 1, "path": "/x", "method": "GET"}, {"_id": 2, "path": "/y", "method": "GET"}], 10),
                 ([{"_id": 3, "path": "/z", "method": "GET"}, {"_id": 4, "path": "/w", "method": "GET"}], 10)]
        self._patch_pages(pages)
        with self.assertRaises(common.YapiSkillError):
            common.find_interface_by_path_method(fake_config(), 1, "/a", "get")


    def test_empty_project_returns_none(self):
        self._patch_pages([([], 0)])
        self.assertIsNone(common.find_interface_by_path_method(fake_config(), 1, "/a", "get"))

    def test_missing_total_short_page_is_complete(self):
        # total 缺失但末页不足一页 => 视为完整扫描 => 未命中返回 None（不 fail-closed）
        def fake(config, pid, page, limit):
            if page == 1:
                return {"list": [{"_id": 1, "path": "/b", "method": "GET"}]}
            return {"list": []}
        common.yapi_list_interfaces_raw = fake
        self.assertIsNone(common.find_interface_by_path_method(fake_config(), 1, "/a", "get"))

    def test_missing_total_full_pages_fail_closed(self):
        # total 缺失且每页填满、用满 max_pages => 无法确认扫完 => 抛错
        def fake(config, pid, page, limit):
            return {"list": [{"_id": page * 10, "path": f"/p{page}a", "method": "GET"},
                             {"_id": page * 10 + 1, "path": f"/p{page}b", "method": "GET"}]}
        common.yapi_list_interfaces_raw = fake
        with self.assertRaises(common.YapiSkillError):
            common.find_interface_by_path_method(fake_config(), 1, "/a", "get")


    def test_single_match_but_incomplete_scan_fails_closed(self):
        # 命中 1 个，但 total 远大于已扫描数（未完整）=> 不能证明唯一 => 抛
        def fake(config, pid, page, limit):
            if page == 1:
                return {"list": [{"_id": 1, "path": "/a", "method": "GET"},
                                 {"_id": 2, "path": "/b", "method": "GET"}], "total": 100}
            return {"list": [{"_id": page * 10, "path": f"/x{page}", "method": "GET"},
                             {"_id": page * 10 + 1, "path": f"/y{page}", "method": "GET"}], "total": 100}
        common.yapi_list_interfaces_raw = fake
        with self.assertRaises(common.YapiSkillError):
            common.find_interface_by_path_method(fake_config(), 1, "/a", "get")

    def test_malformed_list_raises(self):
        # list 字段缺失/非数组 => 异常响应，不能当成"空项目/末页" => 抛
        common.yapi_list_interfaces_raw = lambda config, pid, page, limit: {"total": 5}
        with self.assertRaises(common.YapiSkillError):
            common.find_interface_by_path_method(fake_config(), 1, "/a", "get")


    def test_negative_total_not_treated_as_complete(self):
        # total 为负（异常值）不能被当作完整扫描；未命中且填满 max_pages => fail closed
        def fake(config, pid, page, limit):
            return {"list": [{"_id": page * 10, "path": f"/x{page}", "method": "GET"},
                             {"_id": page * 10 + 1, "path": f"/y{page}", "method": "GET"}], "total": -1}
        common.yapi_list_interfaces_raw = fake
        with self.assertRaises(common.YapiSkillError):
            common.find_interface_by_path_method(fake_config(), 1, "/a", "get")


class TestMergeParameters(unittest.TestCase):
    def test_op_overrides_path_level_and_keeps_others(self):
        path_level = [{"in": "query", "name": "a", "description": "path-a"},
                      {"in": "header", "name": "H", "description": "h"}]
        op_level = [{"in": "query", "name": "a", "description": "op-a"}]
        by = {(p["in"], p["name"]): p for p in o2y._merge_parameters(path_level, op_level)}
        self.assertEqual(by[("query", "a")]["description"], "op-a")
        self.assertIn(("header", "H"), by)


class TestConvert(unittest.TestCase):
    def test_path_level_params_merged(self):
        spec = {"paths": {"/x/{id}": {
            "parameters": [{"in": "path", "name": "id", "required": True, "schema": {"type": "string"}}],
            "get": {"summary": "Get X", "tags": ["T"],
                    "parameters": [{"in": "query", "name": "q", "description": "kw"}],
                    "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}}},
        }}}
        payload, tag, warns = o2y.convert(spec, "/x/{id}", "get")
        self.assertEqual(tag, "T")
        self.assertIn("id", {p["name"] for p in payload.get("req_params", [])})
        self.assertTrue(any(p["name"] == "q" for p in payload.get("req_query", [])))

    def test_non_json_request_body_warns(self):
        spec = {"paths": {"/y": {"post": {
            "requestBody": {"content": {"application/xml": {"schema": {}}}}, "responses": {}}}}}
        payload, tag, warns = o2y.convert(spec, "/y", "post")
        self.assertTrue(any("application/json" in w for w in warns))
        self.assertNotIn("req_body_other", payload)


class TestUpsertArtifact(unittest.TestCase):
    def _run(self, payload_dict, existing):
        tmp = Path(self._d)
        pf = tmp / "payload.json"
        pf.write_text(json.dumps(payload_dict), encoding="utf-8")
        pv = tmp / "preview.json"
        up.load_config = lambda p=None: (fake_config(), None)
        up.yapi_get_cat_menu_raw = lambda c, p: [{"_id": 1, "name": "公共分类"}]
        if existing is None:
            up.find_interface_by_path_method = lambda *a, **k: None
        else:
            up.find_interface_by_path_method = lambda *a, **k: {"_id": existing["_id"]}
            up.yapi_get_interface_detail_raw = lambda c, i, p: existing
        rc = up.main(["--projectId", "1", "--payload", str(pf), "--preview-out", str(pv)])
        return rc, json.loads(pv.read_text(encoding="utf-8"))

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self._d = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def test_update_rmw_and_before_after(self):
        existing = {"_id": 9, "title": "old", "path": "/a", "method": "GET",
                    "markdown": "old-md", "status": "done", "catid": 7, "tag": ["人工"],
                    "mock_extra": "keep"}
        payload = {"title": "new", "path": "/a", "method": "GET", "markdown": "new-md"}
        rc, art = self._run(payload, existing)
        self.assertEqual(rc, 0)
        self.assertEqual(art["mode"], "update")
        fp = art["finalPayload"]
        self.assertEqual(fp["id"], 9)
        self.assertEqual(fp["catid"], 7)            # category kept
        self.assertNotIn("status", fp)              # status never sent
        self.assertEqual(fp["tag"], ["人工"])        # writable field re-sent
        self.assertNotIn("mock_extra", fp)          # non-writable not re-sent
        self.assertEqual(fp["markdown"], "new-md")  # managed field overwritten
        self.assertEqual(art["existingManaged"]["markdown"], "old-md")  # before captured

    def test_create_reports_ignored_fields(self):
        payload = {"title": "t", "path": "/n", "method": "POST", "req_hedaers": [], "status": "x"}
        rc, art = self._run(payload, None)
        self.assertEqual(rc, 0)
        self.assertEqual(art["mode"], "create")
        self.assertEqual(art["ignoredFields"], ["req_hedaers", "status"])


class TestHttpPostJson(unittest.TestCase):
    """Lock the transport-layer encoding the old form-urlencoded path got wrong:
    add/up must send array fields as real JSON arrays (YApi rejects stringified
    "[]" with "应当是 array 类型"). Invisible to the tests above because those mock
    the yapi_*_raw helpers, sitting above the HTTP encoding layer.
    """

    def setUp(self):
        self._orig_urlopen = common.urllib.request.urlopen
        self.captured = {}

        class _FakeResp:
            def __init__(self, body):
                self._b = body

            def read(self):
                return self._b

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None, context=None):
            self.captured["data"] = req.data
            self.captured["headers"] = {k.lower(): v for k, v in req.header_items()}
            return _FakeResp(json.dumps({"errcode": 0, "errmsg": "ok", "data": {"n": 1}}).encode("utf-8"))

        common.urllib.request.urlopen = fake_urlopen

    def tearDown(self):
        common.urllib.request.urlopen = self._orig_urlopen

    def test_arrays_sent_as_real_json_arrays(self):
        fields = {
            "id": 9, "title": "t",
            "req_query": [], "req_headers": [{"name": "Content-Type"}],
            "req_body_form": [], "req_params": [], "tag": [],
            "req_body_is_json_schema": True,
        }
        common.http_post_json("http://x/api/interface/up", fields, 60, True)
        self.assertIn("application/json", self.captured["headers"].get("content-type", ""))
        sent = json.loads(self.captured["data"].decode("utf-8"))
        for k in ("req_query", "req_headers", "req_body_form", "req_params", "tag"):
            self.assertIsInstance(sent[k], list, f"{k} must be a JSON array, got {type(sent[k]).__name__}")
        self.assertEqual(sent["req_headers"], [{"name": "Content-Type"}])
        self.assertIs(sent["req_body_is_json_schema"], True)  # bool stays bool, not "true"

    def test_none_values_dropped(self):
        common.http_post_json("http://x/api/interface/up", {"a": 1, "b": None}, 60, True)
        sent = json.loads(self.captured["data"].decode("utf-8"))
        self.assertEqual(sent, {"a": 1})

    def test_add_cat_still_form_encoded(self):
        # add_cat stays form-urlencoded (flat scalars; the OpenAPI doc mandates it)
        common.http_post_form(
            "http://x/api/interface/add_cat",
            {"name": "c", "project_id": 1, "token": "t"}, 60, True,
        )
        self.assertIn("application/x-www-form-urlencoded", self.captured["headers"].get("content-type", ""))
        self.assertIn("name=c", self.captured["data"].decode("utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
