from __future__ import annotations

from cip.modules.source_activation.infrastructure.osint_framework import parse_osint_framework


def test_osint_framework_parser_preserves_category_path_and_deduplicates() -> None:
    payload = """
    {
      "name": "OSINT Framework",
      "children": [
        {
          "name": "Username",
          "children": [
            {"name": "Sherlock", "url": "https://github.com/sherlock-project/sherlock"},
            {"name": "Sherlock", "url": "https://github.com/sherlock-project/sherlock"},
            {"name": "Bad", "url": "javascript:alert(1)"}
          ]
        }
      ]
    }
    """

    candidates = parse_osint_framework(payload)

    assert len(candidates) == 1
    assert candidates[0].name == "Sherlock"
    assert candidates[0].hostname == "github.com"
    assert candidates[0].category_path == ("OSINT Framework", "Username")


def test_parser_accepts_alternate_link_and_label_keys() -> None:
    payload = '{"label":"DNS","items":[{"title":"Tool","href":"https://example.test/a"}]}'

    candidates = parse_osint_framework(payload)

    assert candidates[0].name == "Tool"
    assert candidates[0].url == "https://example.test/a"
    assert candidates[0].category_path == ("DNS",)
