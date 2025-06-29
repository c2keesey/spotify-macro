"""Tests for flow logic edge cases in playlist flow automation."""

import pytest
from unittest.mock import Mock, MagicMock
from macros.spotify.playlist_flow.action import (
    build_playlist_relationships, 
    detect_cycles,
    flow_songs_to_parents
)


class TestFlowLogicEdgeCases:
    """Test flow logic edge cases."""

    def create_mock_spotify_client(self, playlists):
        """Create a mock Spotify client with predefined playlists."""
        sp = Mock()
        
        # Mock current_user_playlists to return our test playlists
        playlist_items = [
            {"id": pid, "name": name} 
            for pid, name in playlists.items()
        ]
        
        sp.current_user_playlists.return_value = {
            "items": playlist_items
        }
        
        return sp

    def test_character_conflicts_flow_to_both_parents(self):
        """Test that a child flows to multiple parents with overlapping characters."""
        # Setup: Child with 🜀 flows to both 🜀 parent and 🜀🜁 parent
        playlists = {
            "parent1": "🜀 Collection One",
            "parent2": "🜀🜁 Collection Two", 
            "child1": "Daily Mix 🜀"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Child should flow to both parents
        assert "child1" in parent_to_children["parent1"]
        assert "child1" in parent_to_children["parent2"]
        
        # Child should have both parents
        assert "parent1" in child_to_parents["child1"]
        assert "parent2" in child_to_parents["child1"]

    def test_multiple_children_additive_flows(self):
        """Test that multiple children flow additively to same parent."""
        playlists = {
            "parent1": "🜀 Collection",
            "child1": "Mix One 🜀",
            "child2": "Mix Two 🜀", 
            "child3": "Mix Three 🜀"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # All children should flow to parent
        expected_children = {"child1", "child2", "child3"}
        actual_children = set(parent_to_children["parent1"])
        assert actual_children == expected_children

    def test_orphaned_relationships_skipped_silently(self):
        """Test that children without matching parents are skipped silently."""
        playlists = {
            "parent1": "🜀 Collection",
            "child1": "Mix 🜀",        # Has matching parent
            "child2": "Mix 🜁",        # No matching parent (orphaned)
            "child3": "Mix 🜂"         # No matching parent (orphaned)
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Only child1 should have a relationship
        assert "child1" in parent_to_children["parent1"]
        assert "child2" not in parent_to_children.get("parent1", [])
        assert "child3" not in parent_to_children.get("parent1", [])
        
        # Orphaned children should not appear in child_to_parents
        assert "child1" in child_to_parents
        assert "child2" not in child_to_parents
        assert "child3" not in child_to_parents

    def test_self_reference_ignored(self):
        """Test that self-referencing playlists are ignored."""
        playlists = {
            "self_ref": "🜀 Self Mix 🜀",
            "normal_parent": "🜁 Collection",
            "normal_child": "Mix 🜁"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Self-referencing playlist should not appear in relationships
        assert "self_ref" not in parent_to_children
        assert "self_ref" not in child_to_parents
        
        # Normal relationship should work
        assert "normal_child" in parent_to_children["normal_parent"]

    def test_cycle_detection(self):
        """Test cycle detection in flow relationships."""
        playlists = {
            "cycle_a": "🜀 Cycle A 🜁",
            "cycle_b": "🜁 Cycle B 🜀",
            "normal_parent": "🜂 Collection",
            "normal_child": "Mix 🜂"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Detect cycles
        cycles = detect_cycles(child_to_parents)
        
        # Should detect one cycle
        assert len(cycles) >= 1
        
        # Cycle should involve both playlists
        cycle_playlists = set()
        for cycle in cycles:
            cycle_playlists.update(cycle)
        
        assert "cycle_a" in cycle_playlists
        assert "cycle_b" in cycle_playlists

    def test_complex_multi_character_relationships(self):
        """Test complex relationships with multiple characters."""
        playlists = {
            "multi_parent": "🜀🜁🜂 Multi Parent",
            "single_child1": "Child One 🜀", 
            "single_child2": "Child Two 🜁",
            "single_child3": "Child Three 🜂",
            "multi_child": "Multi Child 🜀🜁",
            "dual_role": "🜀 Dual Role 🜃"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Multi parent should receive from all matching children
        multi_parent_children = set(parent_to_children["multi_parent"])
        expected_children = {"single_child1", "single_child2", "single_child3", "multi_child"}
        assert multi_parent_children == expected_children
        
        # Multi child should flow to multi parent for both chars
        assert "multi_parent" in child_to_parents["multi_child"]
        
        # Dual role should be both parent and child
        assert "dual_role" in parent_to_children  # Has parent chars
        assert "dual_role" in child_to_parents    # Has child chars

    def test_empty_playlists_handled(self):
        """Test that empty playlist names are handled gracefully."""
        playlists = {
            "normal": "🜀 Collection",
            "empty": "",
            "whitespace": "   ",
            "child": "Mix 🜀"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Empty and whitespace playlists should not create relationships
        assert "empty" not in parent_to_children
        assert "whitespace" not in parent_to_children
        
        # Normal relationship should still work
        assert "child" in parent_to_children["normal"]

    def test_special_characters_only_names(self):
        """Test playlist names with only special characters."""
        playlists = {
            "special_only": "🜀🜁🜂",  # Only special chars, no letters
            "normal_parent": "🜀 Collection",
            "child": "Mix 🜀"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Special-only playlist should not create relationships (no normal letters)
        assert "special_only" not in parent_to_children
        assert "special_only" not in child_to_parents
        
        # Normal relationship should work
        assert "child" in parent_to_children["normal_parent"]

    def test_unicode_normalization_in_relationships(self):
        """Test that Unicode normalization works in relationship building."""
        # Test with combining characters vs precomposed
        playlists = {
            "parent1": "🜀 Café Collection",      # Precomposed é
            "parent2": "🜀 Cafe\u0301 Collection", # Combining é  
            "child": "Mix 🜀"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Both parents should be detected (they have different IDs but similar names)
        assert "child" in parent_to_children["parent1"]
        assert "child" in parent_to_children["parent2"]

    @pytest.mark.slow
    def test_large_scale_relationships(self):
        """Test performance with many playlists and relationships."""
        # Create many playlists with overlapping relationships
        playlists = {}
        
        # Create 10 parent playlists for each of 5 characters
        chars = ['🜀', '🜁', '🜂', '🜃', '🜄']
        for i, char in enumerate(chars):
            for j in range(10):
                playlists[f"parent_{i}_{j}"] = f"{char} Parent {i}-{j}"
        
        # Create 50 child playlists with random character combinations
        import random
        for i in range(50):
            selected_chars = random.sample(chars, random.randint(1, 3))
            char_suffix = ''.join(selected_chars)
            playlists[f"child_{i}"] = f"Child {i} {char_suffix}"
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Should handle large number of relationships without error
        assert len(playlists_dict) == len(playlists)
        assert len(parent_to_children) > 0
        assert len(child_to_parents) > 0

    def test_transitive_flow_chains(self):
        """Test transitive flow chains (A🜀 → 🜀B🜁 → 🜁C)."""
        # Note: Current implementation does direct flows only
        # This test documents the current behavior
        playlists = {
            "chain_start": "Start 🜀",
            "chain_middle": "🜀 Middle 🜁", 
            "chain_end": "🜁 End"
        }
        
        sp = self.create_mock_spotify_client(playlists)
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        # Direct relationships should exist
        assert "chain_start" in parent_to_children["chain_middle"]
        assert "chain_middle" in parent_to_children["chain_end"]
        
        # Transitive relationship (Start → End) should NOT exist in current implementation
        # (This is the expected behavior - only direct relationships)
        assert "chain_start" not in parent_to_children.get("chain_end", [])