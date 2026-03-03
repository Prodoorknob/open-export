"""Tests for open_export.exporter."""

from open_export.exporter import (
    _extract_message_text,
    _safe_filename,
    linearize_conversation,
)


class TestLinearizeConversation:
    def test_simple_two_turn(self):
        conv = {
            "mapping": {
                "root": {
                    "id": "root",
                    "parent": None,
                    "children": ["msg1"],
                    "message": None,
                },
                "msg1": {
                    "id": "msg1",
                    "parent": "root",
                    "children": ["msg2"],
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Hello"]},
                    },
                },
                "msg2": {
                    "id": "msg2",
                    "parent": "msg1",
                    "children": [],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Hi there!"]},
                    },
                },
            }
        }
        messages = linearize_conversation(conv)
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "text": "Hello"}
        assert messages[1] == {"role": "assistant", "text": "Hi there!"}

    def test_branching_takes_last_child(self):
        conv = {
            "mapping": {
                "root": {
                    "id": "root",
                    "parent": None,
                    "children": ["msg1"],
                    "message": None,
                },
                "msg1": {
                    "id": "msg1",
                    "parent": "root",
                    "children": ["old_reply", "new_reply"],
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Q"]},
                    },
                },
                "old_reply": {
                    "id": "old_reply",
                    "parent": "msg1",
                    "children": [],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Old"]},
                    },
                },
                "new_reply": {
                    "id": "new_reply",
                    "parent": "msg1",
                    "children": [],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["New"]},
                    },
                },
            }
        }
        messages = linearize_conversation(conv)
        assert len(messages) == 2
        assert messages[1]["text"] == "New"

    def test_empty_mapping(self):
        assert linearize_conversation({}) == []
        assert linearize_conversation({"mapping": {}}) == []

    def test_skips_system_messages(self):
        conv = {
            "mapping": {
                "root": {
                    "id": "root",
                    "parent": None,
                    "children": ["sys"],
                    "message": None,
                },
                "sys": {
                    "id": "sys",
                    "parent": "root",
                    "children": ["msg1"],
                    "message": {
                        "author": {"role": "system"},
                        "content": {"parts": ["You are..."]},
                    },
                },
                "msg1": {
                    "id": "msg1",
                    "parent": "sys",
                    "children": [],
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Hi"]},
                    },
                },
            }
        }
        messages = linearize_conversation(conv)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"


class TestSafeFilename:
    def test_basic(self):
        result = _safe_filename("My Chat", "abcdef12-3456")
        assert result == "My Chat_abcdef12"

    def test_unsafe_chars(self):
        result = _safe_filename('Chat: "Hello" <world>', "abcdef12")
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert ":" not in result

    def test_truncation(self):
        long_title = "A" * 200
        result = _safe_filename(long_title, "abcdef12")
        assert len(result) < 200

    def test_empty_title(self):
        result = _safe_filename("", "abcdef12")
        assert "Untitled" in result


class TestExtractMessageText:
    def test_string_parts(self):
        msg = {"content": {"parts": ["Hello", " world"]}}
        assert _extract_message_text(msg) == "Hello\n world"

    def test_dict_parts_with_text(self):
        msg = {"content": {"parts": [{"text": "code output"}]}}
        assert _extract_message_text(msg) == "code output"

    def test_image_part(self):
        msg = {"content": {"parts": [{"content_type": "image_asset_pointer"}]}}
        assert _extract_message_text(msg) == "[Image]"

    def test_empty_content(self):
        msg = {"content": {"parts": []}}
        assert _extract_message_text(msg) == ""

    def test_missing_content(self):
        msg = {}
        assert _extract_message_text(msg) == ""
