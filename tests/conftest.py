"""Pytest configuration and shared fixtures for playlist flow tests."""

import pytest
from tests.playlist_flow_test_utils import (
    PlaylistFlowTestUtils,
    test_utils,
    clean_test_utils,
    sample_tracks,
    basic_flow_scenario,
    cycle_scenario,
    unicode_scenario,
    self_reference_scenario,
    multi_hop_scenario,
    large_playlist_scenario,
    cleanup_before_session
)

# Import all fixtures from test utils so they're available to all test files
__all__ = [
    'test_utils',
    'clean_test_utils', 
    'sample_tracks',
    'basic_flow_scenario',
    'cycle_scenario',
    'unicode_scenario',
    'self_reference_scenario',
    'multi_hop_scenario',
    'large_playlist_scenario',
    'cleanup_before_session'
]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "spotify: mark test as requiring Spotify API access"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "cleanup: mark test as cleanup test"
    )
    config.addinivalue_line(
        "markers", "cycle: mark test as cycle detection test"
    )
    config.addinivalue_line(
        "markers", "unicode: mark test as unicode handling test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add spotify marker to all playlist flow tests
        if "playlist_flow" in str(item.fspath):
            item.add_marker(pytest.mark.spotify)
            item.add_marker(pytest.mark.integration)
            
        # Add slow marker to performance tests
        if "performance" in item.name:
            item.add_marker(pytest.mark.slow)


def pytest_runtest_setup(item):
    """Setup hook that runs before each test."""
    # Skip spotify tests if running without spotify access
    spotify_markers = [mark for mark in item.iter_markers(name="spotify")]
    if spotify_markers:
        # Could add environment check here
        pass


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    print("\n🎵 Starting Spotify Playlist Flow Test Suite")
    print("⚠️  This will create and delete test playlists in your Spotify account")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    if exitstatus == 0:
        print("\n✅ All tests passed! Test playlists have been cleaned up.")
    else:
        print(f"\n❌ Tests finished with exit status: {exitstatus}")
        print("🧹 Attempting final cleanup of test playlists...")
        try:
            utils = PlaylistFlowTestUtils()
            utils.cleanup_all_test_playlists()
            print("✅ Final cleanup completed")
        except Exception as e:
            print(f"❌ Final cleanup failed: {e}")


# Custom pytest options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--cleanup-only",
        action="store_true",
        default=False,
        help="Only run cleanup, don't run tests"
    )
    parser.addoption(
        "--skip-slow",
        action="store_true", 
        default=False,
        help="Skip slow/performance tests"
    )


def pytest_configure(config):
    """Configure pytest based on custom options."""
    if config.getoption("--cleanup-only"):
        # Only run cleanup
        utils = PlaylistFlowTestUtils()
        utils.cleanup_all_test_playlists()
        pytest.exit("✅ Cleanup completed", returncode=0)
    
    if config.getoption("--skip-slow"):
        # Skip slow tests
        config.option.markexpr = "not slow"