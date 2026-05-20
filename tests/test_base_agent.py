"""Tests for BaseAgent._parse_json_response()."""

from __future__ import annotations

import json

import pytest

from src.agents.base_agent import BaseAgent


def test_parse_json_response_raw_json():
    raw = '{"key": "value", "number": 42}'
    result = BaseAgent._parse_json_response(raw)
    assert result == {"key": "value", "number": 42}


def test_parse_json_response_fenced_with_language_tag():
    fenced = '```json\n{"overall_assessment": "unsupported", "confidence": "high"}\n```'
    result = BaseAgent._parse_json_response(fenced)
    assert result["overall_assessment"] == "unsupported"
    assert result["confidence"] == "high"


def test_parse_json_response_fenced_without_language_tag():
    fenced = '```\n{"key": "value"}\n```'
    result = BaseAgent._parse_json_response(fenced)
    assert result == {"key": "value"}


def test_parse_json_response_strips_leading_trailing_whitespace():
    raw = '   \n  {"key": "value"}  \n   '
    result = BaseAgent._parse_json_response(raw)
    assert result == {"key": "value"}


def test_parse_json_response_malformed_raises_value_error():
    with pytest.raises(ValueError, match="not valid JSON"):
        BaseAgent._parse_json_response("this is not json at all")


def test_parse_json_response_malformed_with_partial_fence_raises():
    with pytest.raises(ValueError, match="not valid JSON"):
        BaseAgent._parse_json_response("```json\nnot json\n```")


def test_parse_json_response_nested_object():
    raw = json.dumps({"procedures": [{"cdt_code": "D2750", "verdict": "unsupported"}]})
    result = BaseAgent._parse_json_response(raw)
    assert result["procedures"][0]["cdt_code"] == "D2750"


def test_parse_json_response_fenced_multiline_json():
    fenced = '```json\n{\n  "key": "value",\n  "list": [1, 2, 3]\n}\n```'
    result = BaseAgent._parse_json_response(fenced)
    assert result["list"] == [1, 2, 3]
