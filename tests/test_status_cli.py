"""Tests for opengrid.cli.commands.status 的 JSON 五态输出

inventory.status 是 Agent 判断"真没货 vs 配置坏"的关键字段，前评审发现
完全没测。本文件覆盖 loaded / empty / unconfigured / not_found / invalid 五态。
"""
import json
from unittest.mock import patch

from opengrid.cli.commands import status as status_cmd


def _run_and_capture_json(capsys):
    """模拟 `status --json` 调用，返回解析后的 JSON dict。"""
    class _Args:
        json = True

    status_cmd.handle_status(_Args())
    out = capsys.readouterr().out
    return json.loads(out)


def test_status_json_loaded(capsys, monkeypatch):
    """配置 OK + 文件 OK + 有库存 → loaded。"""
    monkeypatch.setattr(
        status_cmd, "load_inventory",
        lambda cfg: {"8x8": 3, "6x6": 1},
    )
    monkeypatch.setattr(
        status_cmd, "get_inventory_path",
        lambda cfg: "/tmp/inv.json",
    )
    payload = _run_and_capture_json(capsys)
    assert payload["inventory"]["status"] == "loaded"
    assert payload["inventory"]["total_count"] == 4


def test_status_json_empty(capsys, monkeypatch):
    """配置 OK + 文件 OK + 库存为空 → empty。"""
    monkeypatch.setattr(status_cmd, "load_inventory", lambda cfg: {})
    monkeypatch.setattr(status_cmd, "get_inventory_path", lambda cfg: "/tmp/inv.json")
    payload = _run_and_capture_json(capsys)
    assert payload["inventory"]["status"] == "empty"
    assert payload["inventory"]["total_count"] == 0


def test_status_json_unconfigured(capsys, monkeypatch):
    """opengrid_config.yaml 没配 inventory_path → ValueError → unconfigured。"""
    def _raise(_cfg):
        raise ValueError("未配置 inventory_path")
    monkeypatch.setattr(status_cmd, "get_inventory_path", _raise)
    payload = _run_and_capture_json(capsys)
    assert payload["inventory"]["status"] == "unconfigured"
    assert payload["inventory"]["path"] is None


def test_status_json_not_found(capsys, monkeypatch):
    """配了 path 但文件不存在 → FileNotFoundError → not_found。"""
    monkeypatch.setattr(
        status_cmd, "get_inventory_path",
        lambda cfg: "/non/existent/inventory.json",
    )
    def _raise(_cfg):
        raise FileNotFoundError("file gone")
    monkeypatch.setattr(status_cmd, "load_inventory", _raise)
    payload = _run_and_capture_json(capsys)
    assert payload["inventory"]["status"] == "not_found"
    assert payload["inventory"]["path"] == "/non/existent/inventory.json"


def test_status_json_invalid(capsys, monkeypatch):
    """文件存在但 JSON 坏 → JSONDecodeError → invalid。"""
    monkeypatch.setattr(
        status_cmd, "get_inventory_path",
        lambda cfg: "/tmp/corrupted.json",
    )
    def _raise(_cfg):
        raise json.JSONDecodeError("Expecting value", "doc", 0)
    monkeypatch.setattr(status_cmd, "load_inventory", _raise)
    payload = _run_and_capture_json(capsys)
    assert payload["inventory"]["status"] == "invalid"
