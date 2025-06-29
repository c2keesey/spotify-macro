"""Pytest-based tests for playlist flow automation.

These tests create Spotify playlists, run the automation, and validate results.
All test playlists are automatically cleaned up after testing.
"""

import time
import pytest
from typing import Dict, Any
from tests.playlist_flow_test_utils import PlaylistFlowTestUtils
from macros.spotify.playlist_flow.action import run_action


@pytest.mark.spotify
@pytest.mark.integration
class TestPlaylistFlow:
    """Test suite for playlist flow automation using pytest."""

    def validate_results(self, title: str, message: str, expected: Dict[str, Any]) -> Dict[str, Any]:
        """Validate automation results against expected outcomes."""
        validation = {
            "passed": True,
            "issues": []
        }
        
        # Check if flow was expected to succeed
        if expected.get("should_flow", True):
            if "Error" in title:
                validation["passed"] = False
                validation["issues"].append(f"Expected successful flow but got error: {title}")
        
        # Check if cycles were expected
        if "expected_cycles" in expected:
            expected_cycles = expected["expected_cycles"]
            if expected_cycles > 0:
                if "cycle" not in message.lower():
                    validation["passed"] = False
                    validation["issues"].append(f"Expected {expected_cycles} cycles but none mentioned")
            else:
                if "cycle" in message.lower():
                    validation["passed"] = False
                    validation["issues"].append("Did not expect cycles but they were mentioned")
        
        # Check if songs were expected to flow
        if "expected_flow" in expected:
            expected_count = expected["expected_flow"]
            if expected_count > 0:
                if "No New Songs" in title:
                    validation["passed"] = False
                    validation["issues"].append(f"Expected {expected_count} songs to flow but none did")
        
        return validation

    def test_basic_flow(self, basic_flow_scenario):
        """Test basic parent-child flow relationship."""
        # Wait for Spotify to sync
        time.sleep(2)
        
        # Run the automation
        title, message = run_action()
        
        # Validate results
        expected = {"should_flow": True, "expected_flow": 3}
        validation = self.validate_results(title, message, expected)
        
        assert validation["passed"], f"Validation failed: {validation['issues']}"

    @pytest.mark.cycle
    def test_cycle_detection(self, cycle_scenario):
        """Test cycle detection and handling."""
        # Wait for Spotify to sync
        time.sleep(2)
        
        # Run the automation
        title, message = run_action()
        
        # Validate results
        expected = {"should_flow": False, "expected_cycles": 1}
        validation = self.validate_results(title, message, expected)
        
        assert validation["passed"], f"Validation failed: {validation['issues']}"

    @pytest.mark.unicode
    def test_unicode_characters(self, unicode_scenario):
        """Test Unicode and emoji character handling."""
        # Wait for Spotify to sync
        time.sleep(2)
        
        # Run the automation
        title, message = run_action()
        
        # Validate results
        expected = {"should_flow": True, "expected_flow": 2}
        validation = self.validate_results(title, message, expected)
        
        assert validation["passed"], f"Validation failed: {validation['issues']}"

    def test_self_reference(self, self_reference_scenario):
        """Test self-referencing playlist handling."""
        # Wait for Spotify to sync
        time.sleep(2)
        
        # Run the automation
        title, message = run_action()
        
        # Validate results - should not create cycles
        expected = {"should_flow": False, "expected_cycles": 0}
        validation = self.validate_results(title, message, expected)
        
        assert validation["passed"], f"Validation failed: {validation['issues']}"

    def test_multi_hop_chain(self, multi_hop_scenario):
        """Test multi-hop flow chains."""
        # Wait for Spotify to sync
        time.sleep(2)
        
        # Run the automation
        title, message = run_action()
        
        # Validate results
        expected = {"should_flow": True, "expected_flow": 2}
        validation = self.validate_results(title, message, expected)
        
        assert validation["passed"], f"Validation failed: {validation['issues']}"

    @pytest.mark.slow
    @pytest.mark.performance
    def test_performance_large_playlists(self, large_playlist_scenario):
        """Test performance with larger playlists."""
        # Wait for Spotify to sync
        time.sleep(2)
        
        # Run the automation
        title, message = run_action()
        
        # Validate results
        track_count = large_playlist_scenario["track_count"]
        expected = {"should_flow": True, "expected_flow": track_count}
        validation = self.validate_results(title, message, expected)
        
        assert validation["passed"], f"Validation failed: {validation['issues']}"


@pytest.mark.cleanup
class TestCleanup:
    """Tests for cleanup functionality."""
    
    def test_cleanup_all_test_playlists(self, test_utils):
        """Test that cleanup removes all test playlists."""
        # Create a few test playlists
        test_utils.create_test_playlist("Cleanup Test 1")
        test_utils.create_test_playlist("Cleanup Test 2")
        
        # Get count before cleanup
        playlists_before = test_utils.get_all_playlists()
        test_playlists_before = [p for p in playlists_before if p["name"].startswith(test_utils.test_prefix)]
        
        # Run cleanup
        test_utils.cleanup_all_test_playlists()
        
        # Verify cleanup worked
        playlists_after = test_utils.get_all_playlists()
        test_playlists_after = [p for p in playlists_after if p["name"].startswith(test_utils.test_prefix)]
        
        assert len(test_playlists_after) == 0, f"Found {len(test_playlists_after)} test playlists after cleanup"


# Parametrized tests for different scenarios
@pytest.mark.parametrize("scenario_name,expected", [
    ("basic_flow", {"should_flow": True, "expected_flow": 3}),
    ("cycle", {"should_flow": False, "expected_cycles": 1}),
    ("unicode", {"should_flow": True, "expected_flow": 2}),
])
def test_scenario_parametrized(scenario_name, expected, request):
    """Parametrized test that runs different scenarios."""
    # Get the appropriate fixture
    scenario_data = request.getfixturevalue(f"{scenario_name}_scenario")
    
    # Wait for Spotify to sync
    time.sleep(2)
    
    # Run the automation
    title, message = run_action()
    
    # Create test instance for validation
    test_instance = TestPlaylistFlow()
    validation = test_instance.validate_results(title, message, expected)
    
    assert validation["passed"], f"Validation failed for {scenario_name}: {validation['issues']}"


if __name__ == "__main__":
    # Allow running tests directly with python -m pytest
    pytest.main([__file__])