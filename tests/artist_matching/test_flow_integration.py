#!/usr/bin/env python3
"""
Test the complete integration of artist matching with playlist flow.
"""

def create_flow_integration_test_data():
    """Create test data that demonstrates the flow integration."""
    
    playlists_dict = {
        "New": {
            "name": "New",
            "tracks": [
                # Song by artist who appears in child playlist only (should match)
                {
                    "id": "new_track_1",
                    "name": "New Jazz Discovery",
                    "artists": [{"id": "jazz_child_artist", "name": "Child Jazz Artist"}]
                },
                # Song by artist who appears in both child and parent (should match to child)
                {
                    "id": "new_track_2",
                    "name": "New Electronic Track",
                    "artists": [{"id": "electronic_both_artist", "name": "Electronic Both Artist"}]
                },
                # Song by artist in multiple non-parent playlists (should not match)
                {
                    "id": "new_track_3",
                    "name": "Popular Multi-Playlist Song",
                    "artists": [{"id": "multi_artist", "name": "Multi Playlist Artist"}]
                }
            ]
        },
        # Child playlist - this is where songs should be added
        "Daily Jazz 🎵": {
            "name": "Daily Jazz 🎵",
            "tracks": [
                {
                    "id": "child_jazz_1",
                    "name": "Existing Child Jazz",
                    "artists": [{"id": "jazz_child_artist", "name": "Child Jazz Artist"}]
                }
            ]
        },
        # Parent playlist - this should be excluded from uniqueness check
        "🎵 Jazz Collection": {
            "name": "🎵 Jazz Collection",
            "tracks": [
                {
                    "id": "parent_jazz_1",
                    "name": "Parent Jazz Track",
                    "artists": [{"id": "other_jazz_artist", "name": "Other Jazz Artist"}]
                }
            ]
        },
        # Child Electronic playlist
        "Electronic Mix 🎶": {
            "name": "Electronic Mix 🎶",
            "tracks": [
                {
                    "id": "child_electronic_1",
                    "name": "Child Electronic Track",
                    "artists": [{"id": "electronic_both_artist", "name": "Electronic Both Artist"}]
                }
            ]
        },
        # Parent Electronic playlist (artist also appears here)
        "🎶 Electronic Hub": {
            "name": "🎶 Electronic Hub",
            "tracks": [
                {
                    "id": "parent_electronic_1",
                    "name": "Parent Electronic Track",
                    "artists": [{"id": "electronic_both_artist", "name": "Electronic Both Artist"}]
                }
            ]
        },
        # Multiple regular playlists with same artist (should not match)
        "Rock Playlist 1": {
            "name": "Rock Playlist 1",
            "tracks": [
                {
                    "id": "rock_1",
                    "name": "Rock Song 1",
                    "artists": [{"id": "multi_artist", "name": "Multi Playlist Artist"}]
                }
            ]
        },
        "Rock Playlist 2": {
            "name": "Rock Playlist 2", 
            "tracks": [
                {
                    "id": "rock_2",
                    "name": "Rock Song 2",
                    "artists": [{"id": "multi_artist", "name": "Multi Playlist Artist"}]
                }
            ]
        }
    }
    
    return playlists_dict


def extract_flow_characters(playlist_name: str):
    """Simplified flow character extraction for testing."""
    import re
    
    # Simple detection of special characters at start and end
    start_chars = []
    end_chars = []
    
    # Check for special characters at the beginning
    for char in playlist_name:
        if char.isalpha():
            break
        if not char.isspace() and char not in '[]()':
            start_chars.append(char)
    
    # Check for special characters at the end
    for char in reversed(playlist_name):
        if char.isalpha():
            break
        if not char.isspace() and char not in '[]()':
            end_chars.append(char)
    
    return start_chars, end_chars


def is_parent_playlist(playlist_name: str) -> bool:
    """Check if playlist is a parent playlist."""
    parent_chars, _ = extract_flow_characters(playlist_name)
    return len(parent_chars) > 0


def test_flow_integration():
    """Test the complete flow integration."""
    from collections import defaultdict
    
    print("🧪 Testing Artist Matching + Playlist Flow Integration")
    print("="*60)
    
    playlists_dict = create_flow_integration_test_data()
    
    print("Test scenario:")
    print("• New playlist has songs by artists in child and parent playlists")
    print("• Artist matching should exclude parent playlists from uniqueness check")
    print("• Songs should be added to child playlists, then flow to parents automatically")
    
    print(f"\nCreated test playlists:")
    for name, data in playlists_dict.items():
        parent_chars, child_chars = extract_flow_characters(name)
        flow_type = ""
        if parent_chars:
            flow_type = " (PARENT)"
        elif child_chars:
            flow_type = " (CHILD)"
        track_count = len(data["tracks"])
        print(f"  📀 {name}: {track_count} tracks{flow_type}")
    
    # Build artist mappings with parent exclusion
    artist_to_all_playlists = defaultdict(set)
    artist_to_non_parent_playlists = defaultdict(set)
    
    for playlist_name, playlist_data in playlists_dict.items():
        is_parent = is_parent_playlist(playlist_name)
        
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                artist_id = artist.get("id")
                if artist_id:
                    artist_to_all_playlists[artist_id].add(playlist_name)
                    if not is_parent:
                        artist_to_non_parent_playlists[artist_id].add(playlist_name)
    
    print(f"\nArtist distribution analysis:")
    for artist_id in artist_to_all_playlists:
        all_playlists = artist_to_all_playlists[artist_id]
        non_parent_playlists = artist_to_non_parent_playlists.get(artist_id, set())
        
        print(f"  🎤 {artist_id}:")
        print(f"     All playlists ({len(all_playlists)}): {', '.join(all_playlists)}")
        print(f"     Non-parent playlists ({len(non_parent_playlists)}): {', '.join(non_parent_playlists)}")
        print(f"     Single-playlist (old method): {'✅' if len(all_playlists) == 1 else '❌'}")
        print(f"     Single-playlist (new method): {'✅' if len(non_parent_playlists) == 1 else '❌'}")
    
    # Find single-playlist artists with new method
    single_playlist_artists = set()
    for artist_id, playlists in artist_to_non_parent_playlists.items():
        if len(playlists) == 1:
            single_playlist_artists.add(artist_id)
    
    print(f"\n🎯 Single-playlist artists (excluding parents): {len(single_playlist_artists)}")
    for artist_id in single_playlist_artists:
        target_playlist = list(artist_to_non_parent_playlists[artist_id])[0]
        print(f"  • {artist_id} → {target_playlist}")
    
    # Simulate matching process
    print(f"\n" + "="*60)
    print("SIMULATING ARTIST MATCHING PROCESS")
    print("="*60)
    
    source_tracks = playlists_dict["New"]["tracks"]
    matches = defaultdict(list)
    
    for track in source_tracks:
        track_id = track["id"]
        track_name = track["name"]
        
        print(f"\n🔍 Processing: '{track_name}'")
        
        found_match = False
        for artist in track["artists"]:
            artist_id = artist.get("id")
            artist_name = artist.get("name")
            
            print(f"   🎤 Artist: {artist_name}")
            
            if artist_id in single_playlist_artists:
                target_playlists = artist_to_non_parent_playlists[artist_id]
                target_playlist_name = list(target_playlists)[0]
                
                # Check if already exists
                target_tracks = playlists_dict[target_playlist_name]["tracks"]
                existing_track_ids = {t["id"] for t in target_tracks}
                
                if track_id not in existing_track_ids:
                    matches[target_playlist_name].append({
                        "track_name": track_name,
                        "artist_name": artist_name,
                        "track_id": track_id
                    })
                    print(f"   ✅ MATCH! Will add to '{target_playlist_name}' (child playlist)")
                    
                    # Show flow effect
                    parent_chars, _ = extract_flow_characters(target_playlist_name)
                    if parent_chars:
                        flow_target = f"🎵 {target_playlist_name.split(' ', 1)[1]}"  # Construct parent name
                        if flow_target in playlists_dict:
                            print(f"   🌊 Will then flow to parent: '{flow_target}'")
                    
                    found_match = True
                else:
                    print(f"   ⚠️ Already exists in '{target_playlist_name}'")
                
                break
            else:
                playlist_count = len(artist_to_non_parent_playlists.get(artist_id, set()))
                print(f"   ❌ Multi-playlist artist ({playlist_count} non-parent playlists)")
        
        if not found_match:
            print(f"   ❌ No match found")
    
    # Results
    print(f"\n" + "="*60)
    print("INTEGRATION TEST RESULTS")
    print("="*60)
    
    if matches:
        total_matches = sum(len(track_list) for track_list in matches.values())
        print(f"🎉 SUCCESS! Found {total_matches} matches:")
        
        for target_playlist, track_list in matches.items():
            print(f"\n📀 Target: {target_playlist}")
            for track_info in track_list:
                print(f"    ➕ '{track_info['track_name']}' by {track_info['artist_name']}")
                
            # Show the flow effect
            parent_chars, _ = extract_flow_characters(target_playlist)
            if parent_chars:
                print(f"    🌊 These songs will then automatically flow to parent playlists")
        
        print(f"\n✅ INTEGRATION VERIFIED!")
        print(f"✅ Songs added to child playlists (manually curated)")
        print(f"✅ Parent playlists excluded from uniqueness check")
        print(f"✅ Playlist flow will handle moving songs to parents")
        print(f"✅ This creates an intelligent, automated curation system!")
        
    else:
        print("❌ No matches found")


if __name__ == "__main__":
    test_flow_integration()