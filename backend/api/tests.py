from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from datetime import datetime, timezone
from unittest.mock import patch
import pandas as pd


class AuthTests(APITestCase):
    def test_register_returns_tokens(self):
        resp = self.client.post(
            "/api/register/",
            data={"username": "u1", "password": "a1b2c3"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        self.assertTrue(resp.data.get("access"))
        self.assertTrue(resp.data.get("refresh"))

    def test_protected_requires_auth(self):
        resp = self.client.get("/api/watchlist/count/")
        self.assertEqual(resp.status_code, 401)


class WatchlistTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u2", password="a1b2c3")
        token_resp = self.client.post(
            "/api/token/",
            data={"username": "u2", "password": "a1b2c3"},
            format="json",
        )
        self.assertEqual(token_resp.status_code, 200)
        access = token_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_watchlist_group_crud(self):
        create = self.client.post("/api/watchlist-groups/", data={"name": "G1"}, format="json")
        self.assertEqual(create.status_code, 201)
        group_id = str(create.data["id"])

        listed = self.client.get("/api/watchlist-groups/")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(str(g["id"]) == group_id for g in listed.data))

        updated = self.client.patch(f"/api/watchlist-groups/{group_id}/", data={"name": "G2"}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["name"], "G2")

        deleted = self.client.delete(f"/api/watchlist-groups/{group_id}/")
        self.assertEqual(deleted.status_code, 204)

    def test_watchlist_add_remove_and_counts(self):
        count0 = self.client.get("/api/watchlist/count/")
        self.assertEqual(count0.status_code, 200)
        self.assertEqual(count0.data["status"], "success")
        self.assertEqual(count0.data["data"]["default"], 0)

        add_default = self.client.post(
            "/api/watchlist/",
            data={"ts_code": "000001.SZ", "name": "平安银行"},
            format="json",
        )
        self.assertEqual(add_default.status_code, 200)
        self.assertIn(add_default.data.get("status"), {"success", "info"})

        count1 = self.client.get("/api/watchlist/count/")
        self.assertEqual(count1.data["data"]["default"], 1)

        create_group = self.client.post("/api/watchlist-groups/", data={"name": "G1"}, format="json")
        self.assertEqual(create_group.status_code, 201)
        group_id = str(create_group.data["id"])

        add_group = self.client.post(
            "/api/watchlist/",
            data={"ts_code": "000002.SZ", "name": "万科A", "group_id": group_id},
            format="json",
        )
        self.assertEqual(add_group.status_code, 200)
        self.assertIn(add_group.data.get("status"), {"success", "info"})

        count2 = self.client.get("/api/watchlist/count/")
        self.assertEqual(count2.data["data"]["groups"][group_id], 1)

        del_group = self.client.delete(f"/api/watchlist/?ts_code=000002.SZ&group_id={group_id}")
        self.assertEqual(del_group.status_code, 200)

        count3 = self.client.get("/api/watchlist/count/")
        self.assertEqual(count3.data["data"]["groups"][group_id], 0)

        del_default = self.client.delete("/api/watchlist/?ts_code=000001.SZ")
        self.assertEqual(del_default.status_code, 200)

        count4 = self.client.get("/api/watchlist/count/")
        self.assertEqual(count4.data["data"]["default"], 0)

    def test_events_list_and_create(self):
        listed0 = self.client.get("/api/events/?symbol=000001.SZ")
        self.assertEqual(listed0.status_code, 200)
        self.assertEqual(listed0.data["status"], "success")
        self.assertEqual(listed0.data["data"], [])

        now = datetime(2025, 1, 1, 9, 31, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        created = self.client.post(
            "/api/events/",
            data={
                "symbol": "000001.SZ",
                "title": "测试事件",
                "event_type": "test",
                "source": "unit",
                "license_status": "unknown",
                "event_time": now,
                "market_effective_time": now,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "success")

        listed1 = self.client.get("/api/events/?symbol=000001.SZ")
        self.assertEqual(listed1.status_code, 200)
        self.assertEqual(len(listed1.data["data"]), 1)

    def test_signals_requires_symbol(self):
        resp = self.client.get("/api/signals/")
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.ak.stock_zh_a_hist")
    def test_signals_success(self, mock_hist):
        dates = pd.date_range("2024-01-01", periods=220, freq="B")
        close = pd.Series(range(100, 100 + len(dates)), dtype=float)
        df = pd.DataFrame(
            {
                "日期": dates.strftime("%Y-%m-%d"),
                "开盘": (close - 0.5).values,
                "收盘": close.values,
                "最高": (close + 1).values,
                "最低": (close - 1).values,
                "成交量": (100000 + close * 100).values,
            }
        )
        mock_hist.return_value = df

        resp = self.client.get("/api/signals/?symbol=000001.SZ")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        data = resp.data.get("data") or {}
        self.assertEqual(data.get("symbol"), "000001.SZ")
        signals = data.get("signals") or []
        self.assertTrue(len(signals) >= 3)
        self.assertTrue(data.get("timing_report") is not None)

    def test_backtest_requires_symbol(self):
        resp = self.client.post("/api/backtest/", data={"template": "S1"}, format="json")
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.ak.stock_zh_a_hist")
    def test_backtest_success(self, mock_hist):
        dates = pd.date_range("2023-01-02", periods=260, freq="B")
        close = pd.Series(range(100, 100 + len(dates)), dtype=float)
        df = pd.DataFrame(
            {
                "日期": dates.strftime("%Y-%m-%d"),
                "开盘": (close - 0.2).values,
                "收盘": close.values,
                "最高": (close + 0.5).values,
                "最低": (close - 0.8).values,
                "成交量": (200000 + close * 10).values,
            }
        )
        mock_hist.return_value = df

        resp = self.client.post(
            "/api/backtest/",
            data={
                "symbol": "000001.SZ",
                "template": "S1",
                "params": {"ma_fast": 10, "ma_slow": 30},
                "initial_cash": 100000,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        data = resp.data.get("data") or {}
        self.assertEqual((data.get("config") or {}).get("symbol"), "000001.SZ")
        self.assertTrue((data.get("metrics") or {}).get("end_equity") is not None)
        self.assertTrue(isinstance(data.get("equity_curve"), list))

    @patch("api.views.ak.stock_zh_a_hist")
    def test_backtest_s5_success(self, mock_hist):
        dates = pd.date_range("2023-01-02", periods=260, freq="B")
        close = pd.Series(range(100, 100 + len(dates)), dtype=float)
        df = pd.DataFrame(
            {
                "日期": dates.strftime("%Y-%m-%d"),
                "开盘": (close - 0.2).values,
                "收盘": close.values,
                "最高": (close + 0.5).values,
                "最低": (close - 0.8).values,
                "成交量": (200000 + close * 10).values,
            }
        )
        mock_hist.return_value = df

        resp = self.client.post(
            "/api/backtest/",
            data={
                "symbol": "000001.SZ",
                "template": "S5",
                "params": {"entry_n": 20, "exit_n": 10},
                "initial_cash": 100000,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")

    @patch("api.views.ak.stock_zh_a_hist")
    def test_backtest_s4_uses_event_effective_time_and_filters(self, mock_hist):
        dates = pd.date_range("2023-01-02", periods=260, freq="B")
        close = pd.Series(range(100, 100 + len(dates)), dtype=float)
        df = pd.DataFrame(
            {
                "日期": dates.strftime("%Y-%m-%d"),
                "开盘": (close - 0.2).values,
                "收盘": close.values,
                "最高": (close + 0.5).values,
                "最低": (close - 0.8).values,
                "成交量": (200000 + close * 10).values,
            }
        )
        mock_hist.return_value = df

        ev_date = dates[120].to_pydatetime().replace(tzinfo=timezone.utc)
        ev_iso = ev_date.isoformat().replace("+00:00", "Z")

        created = self.client.post(
            "/api/events/",
            data={
                "symbol": "000001.SZ",
                "title": "事件A",
                "event_type": "earnings",
                "source": "unit",
                "license_status": "ok",
                "event_time": ev_iso,
                "market_effective_time": ev_iso,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)

        other_date = dates[140].to_pydatetime().replace(tzinfo=timezone.utc)
        other_iso = other_date.isoformat().replace("+00:00", "Z")
        created2 = self.client.post(
            "/api/events/",
            data={
                "symbol": "000001.SZ",
                "title": "事件B",
                "event_type": "dividend",
                "source": "unit",
                "license_status": "ok",
                "event_time": other_iso,
                "market_effective_time": other_iso,
            },
            format="json",
        )
        self.assertEqual(created2.status_code, 201)

        resp = self.client.post(
            "/api/backtest/",
            data={
                "symbol": "000001.SZ",
                "template": "S4",
                "params": {"event_type": "earnings", "hold_days": 3, "license_whitelist": ["ok"]},
                "initial_cash": 100000,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        data = resp.data.get("data") or {}
        trades = data.get("trades") or []
        self.assertEqual(len(trades), 1)


class AIModelConfigTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u3", password="a1b2c3")
        token_resp = self.client.post(
            "/api/token/",
            data={"username": "u3", "password": "a1b2c3"},
            format="json",
        )
        self.assertEqual(token_resp.status_code, 200)
        access = token_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_ai_models_list_add_select_delete(self):
        resp0 = self.client.get("/api/ai-models/")
        self.assertEqual(resp0.status_code, 200)
        self.assertEqual(resp0.data["status"], "success")
        self.assertEqual(resp0.data["data"]["items"], [])

        empty_key = self.client.post(
            "/api/ai-models/",
            data={"provider": "deepseek", "base_url": "https://api.deepseek.com", "model": "deepseek-chat", "api_key": ""},
            format="json",
        )
        self.assertEqual(empty_key.status_code, 400)

        created1 = self.client.post(
            "/api/ai-models/",
            data={
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "api_key": "sk-test-123456789",
            },
            format="json",
        )
        self.assertEqual(created1.status_code, 201)

        resp1 = self.client.get("/api/user/info/")
        self.assertEqual(resp1.status_code, 200)
        profile1 = resp1.data.get("profile") or {}
        self.assertTrue(profile1.get("active_ai_model_id") is not None)
        self.assertTrue(isinstance(profile1.get("ai_models") or [], list))
        self.assertEqual(len(profile1.get("ai_models") or []), 1)

        dup = self.client.post(
            "/api/ai-models/",
            data={
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "api_key": "sk-test-123456789",
            },
            format="json",
        )
        self.assertEqual(dup.status_code, 200)
        self.assertEqual(dup.data.get("status"), "info")
        self.assertEqual(dup.data.get("code"), "duplicate")

        resp1b = self.client.get("/api/user/info/")
        models1b = (resp1b.data.get("profile") or {}).get("ai_models") or []
        self.assertEqual(len(models1b), 1)

        created2 = self.client.post(
            "/api/ai-models/",
            data={
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-reasoner",
                "api_key": "sk-test-abcdefg",
            },
            format="json",
        )
        self.assertEqual(created2.status_code, 201)

        resp2 = self.client.get("/api/user/info/")
        profile2 = resp2.data.get("profile") or {}
        models2 = profile2.get("ai_models") or []
        self.assertEqual(len(models2), 2)
        active2 = str(profile2.get("active_ai_model_id"))
        self.assertTrue(any(str(m["id"]) == active2 for m in models2))

        first_id = str(models2[-1]["id"])
        sel = self.client.post(f"/api/ai-models/{first_id}/select/", data={}, format="json")
        self.assertEqual(sel.status_code, 200)

        resp3 = self.client.get("/api/user/info/")
        profile3 = resp3.data.get("profile") or {}
        self.assertEqual(str(profile3.get("active_ai_model_id")), first_id)

        del_resp = self.client.delete(f"/api/ai-models/{first_id}/")
        self.assertEqual(del_resp.status_code, 200)

        resp4 = self.client.get("/api/user/info/")
        profile4 = resp4.data.get("profile") or {}
        models4 = profile4.get("ai_models") or []
        self.assertEqual(len(models4), 1)


class AIAnalyzeErrorTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u4", password="a1b2c3")
        token_resp = self.client.post(
            "/api/token/",
            data={"username": "u4", "password": "a1b2c3"},
            format="json",
        )
        self.assertEqual(token_resp.status_code, 200)
        access = token_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        self.client.post(
            "/api/ai-models/",
            data={
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "api_key": "sk-test-123456789",
            },
            format="json",
        )

        self.client.post(
            "/api/watchlist/",
            data={"ts_code": "000001.SZ", "name": "平安银行"},
            format="json",
        )

    @patch("api.views.deepseek_chat_completion")
    def test_ai_analyze_returns_structured_error_not_500(self, mock_chat):
        from api.views import AIProviderError
        mock_chat.side_effect = AIProviderError(code="invalid_api_key", message="AI 鉴权失败，请检查 API Key 是否正确", status_code=401)
        resp = self.client.post("/api/ai/analyze/", data={}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "error")
        self.assertEqual(resp.data.get("code"), "invalid_api_key")
        self.assertTrue("鉴权失败" in (resp.data.get("message") or ""))
