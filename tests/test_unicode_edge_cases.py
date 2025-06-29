"""Tests for Unicode edge case handling in playlist flow automation."""

import pytest
from macros.spotify.playlist_flow.action import extract_flow_characters


class TestUnicodeEdgeCases:
    """Test Unicode and character handling edge cases."""

    def test_multi_byte_emoji_composite(self):
        """Test multi-byte composite emoji like ❇️ (❇ + ️)"""
        # Test composite emoji at start
        parent_chars, child_chars = extract_flow_characters("❇️ Collection")
        assert len(parent_chars) == 1
        assert parent_chars[0] == "❇️"
        assert child_chars == []
        
        # Test composite emoji at end
        parent_chars, child_chars = extract_flow_characters("Mix ❇️")
        assert parent_chars == []
        assert len(child_chars) == 1
        assert child_chars[0] == "❇️"

    def test_emoji_with_modifiers(self):
        """Test emoji with skin tone modifiers - keep variations separate"""
        # Different skin tone modifiers should be treated as different characters
        parent_chars1, _ = extract_flow_characters("👨🏾‍💻 Collection")
        parent_chars2, _ = extract_flow_characters("👨‍💻 Collection")
        
        assert len(parent_chars1) == 1
        assert len(parent_chars2) == 1
        assert parent_chars1[0] != parent_chars2[0]  # Should be different

    def test_unicode_normalization_nfc(self):
        """Test Unicode normalization to NFC form"""
        # Test combining characters vs precomposed
        # é can be represented as single char (U+00E9) or e + combining accent (U+0065 U+0301)
        single_e = "é Collection"  # Single precomposed character
        combined_e = "e\u0301 Collection"  # e + combining acute accent
        
        parent_chars1, _ = extract_flow_characters(single_e)
        parent_chars2, _ = extract_flow_characters(combined_e)
        
        # After NFC normalization, both should be treated the same
        # Both should have no parent chars since é is not a special character
        assert parent_chars1 == parent_chars2 == []

    def test_zero_width_characters_stripped(self):
        """Test that zero-width characters are stripped"""
        # Test with zero-width space
        parent_chars, _ = extract_flow_characters("🜀\u200B Mix")  # Zero Width Space
        assert len(parent_chars) == 1
        assert parent_chars[0] == "🜀"
        
        # Test with multiple zero-width characters
        parent_chars, _ = extract_flow_characters("🜁\u200C\u200D Mix")  # ZWNJ + ZWJ
        assert len(parent_chars) == 1
        assert parent_chars[0] == "🜁"

    def test_multiple_special_chars_start(self):
        """Test multiple special characters at start for multi-flow"""
        parent_chars, child_chars = extract_flow_characters("🜀🜁 Multi Collection")
        assert len(parent_chars) == 2
        assert "🜀" in parent_chars
        assert "🜁" in parent_chars
        assert child_chars == []

    def test_multiple_special_chars_end(self):
        """Test multiple special characters at end for multi-flow"""
        parent_chars, child_chars = extract_flow_characters("Multi Mix 🜂🜃")
        assert parent_chars == []
        assert len(child_chars) == 2
        assert "🜂" in child_chars
        assert "🜃" in child_chars

    def test_multiple_special_chars_both_ends(self):
        """Test multiple special characters at both start and end"""
        parent_chars, child_chars = extract_flow_characters("🜀🜁 Multi Hub 🜂🜃")
        assert len(parent_chars) == 2
        assert "🜀" in parent_chars
        assert "🜁" in parent_chars
        assert len(child_chars) == 2
        assert "🜂" in child_chars
        assert "🜃" in child_chars

    def test_self_reference_ignored(self):
        """Test self-referencing playlists are ignored"""
        # Single character self-reference
        parent_chars, child_chars = extract_flow_characters("🜀 Self Mix 🜀")
        assert parent_chars == []
        assert child_chars == []
        
        # Multiple character with overlap
        parent_chars, child_chars = extract_flow_characters("🜀🜁 Multi Mix 🜁🜂")
        assert parent_chars == []  # Should be empty due to 🜁 overlap
        assert child_chars == []

    def test_alchemical_symbols(self):
        """Test alchemical symbols are detected as special characters"""
        # Test various alchemical symbols
        alchemical_symbols = ["🜀", "🜁", "🜂", "🜃", "🜄", "🜅", "🜆", "🜇"]
        
        for symbol in alchemical_symbols:
            # Test as parent
            parent_chars, _ = extract_flow_characters(f"{symbol} Collection")
            assert len(parent_chars) == 1
            assert parent_chars[0] == symbol
            
            # Test as child
            _, child_chars = extract_flow_characters(f"Mix {symbol}")
            assert len(child_chars) == 1
            assert child_chars[0] == symbol

    def test_mixed_character_types(self):
        """Test mixing different types of special characters"""
        # Mix emoji, alchemical symbols, and other Unicode symbols
        parent_chars, child_chars = extract_flow_characters("🎵🜀★ Mixed Collection ♪🜁☆")
        
        assert len(parent_chars) == 3
        expected_parents = {"🎵", "🜀", "★"}
        assert set(parent_chars) == expected_parents
        
        assert len(child_chars) == 3
        expected_children = {"♪", "🜁", "☆"}
        assert set(child_chars) == expected_children

    def test_flag_emoji(self):
        """Test flag emoji (multi-codepoint sequences)"""
        # Flag emoji are sequences of regional indicator symbols
        parent_chars, _ = extract_flow_characters("🇺🇸 American Collection")
        assert len(parent_chars) == 1
        assert parent_chars[0] == "🇺🇸"
        
        _, child_chars = extract_flow_characters("Mix 🇺🇸")
        assert len(child_chars) == 1
        assert child_chars[0] == "🇺🇸"

    def test_complex_zwj_sequences(self):
        """Test complex ZWJ (Zero Width Joiner) sequences"""
        # Family emoji using ZWJ sequences
        complex_emoji = "👨‍👩‍👧‍👦"  # Family: man, woman, girl, boy
        
        parent_chars, _ = extract_flow_characters(f"{complex_emoji} Family Collection")
        assert len(parent_chars) == 1
        assert parent_chars[0] == complex_emoji

    def test_empty_after_normalization(self):
        """Test names that become empty after normalization"""
        # Name with only zero-width characters
        parent_chars, child_chars = extract_flow_characters("\u200B\u200C\u200D")
        assert parent_chars == []
        assert child_chars == []
        
        # Name with only whitespace after normalization
        parent_chars, child_chars = extract_flow_characters("   ")
        assert parent_chars == []
        assert child_chars == []

    def test_test_prefix_handling(self):
        """Test that test prefixes are properly stripped before processing"""
        # Test prefix should be stripped
        parent_chars, _ = extract_flow_characters("🧪TEST_🜀 Collection")
        assert len(parent_chars) == 1
        assert parent_chars[0] == "🜀"
        
        # Without test prefix for comparison
        parent_chars2, _ = extract_flow_characters("🜀 Collection")
        assert parent_chars == parent_chars2