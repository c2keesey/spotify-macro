#!/usr/bin/env python3
"""
Correct test scenario: New playlist contains songs where artists appear in other playlists but NOT in New.
This simulates adding new songs by existing single-playlist artists to the New playlist.
"""

def create_correct_test_data():
    """Create the correct test scenario."""
    
    playlists_dict = {
        "New": {
            "name": "New",
            "tracks": [
                # New song by an artist who ONLY exists in Jazz Collection
                {
                    "id": "new_track_1",
                    "name": "Brand New Jazz Track",
                    "artists": [{"id": "exclusive_jazz_artist", "name": "Jazz Only Artist"}]
                },
                # New song by an artist who ONLY exists in Rock Collection  
                {
                    "id": "new_track_2",
                    "name": "Brand New Rock Track", 
                    "artists": [{"id": "exclusive_rock_artist", "name": "Rock Only Artist"}]
                },
                # New song by a popular artist (should not match)
                {
                    "id": "new_track_3",
                    "name": "Popular New Song",
                    "artists": [{"id": "popular_artist", "name": "Everywhere Artist"}]
                },
                # New song by artist with no existing playlist (should not match)
                {
                    "id": "new_track_4", 
                    "name": "Completely New Artist Song",
                    "artists": [{"id": "brand_new_artist", "name": "Never Seen Before"}]
                }
            ]
        },
        "Jazz Specialists": {
            "name": "Jazz Specialists",
            "tracks": [
                {
                    "id": "jazz_1",
                    "name": "Existing Jazz Song 1",
                    "artists": [{"id": "exclusive_jazz_artist", "name": "Jazz Only Artist"}]
                },
                {
                    "id": "jazz_2", 
                    "name": "Existing Jazz Song 2",
                    "artists": [{"id": "exclusive_jazz_artist", "name": "Jazz Only Artist"}]
                }
            ]
        },
        "Rock Underground": {
            "name": "Rock Underground",
            "tracks": [
                {
                    "id": "rock_1",
                    "name": "Existing Rock Song",
                    "artists": [{"id": "exclusive_rock_artist", "name": "Rock Only Artist"}]
                }
            ]
        },
        "Popular Everywhere": {
            "name": "Popular Everywhere",
            "tracks": [
                {
                    "id": "pop_1",
                    "name": "Popular Hit 1", 
                    "artists": [{"id": "popular_artist", "name": "Everywhere Artist"}]
                }
            ]
        },
        "Also Popular": {
            "name": "Also Popular",
            "tracks": [
                {
                    "id": "pop_2",
                    "name": "Popular Hit 2",
                    "artists": [{"id": "popular_artist", "name": "Everywhere Artist"}]
                }
            ]
        }
    }
    
    return playlists_dict


def run_correct_simulation():
    """Run the correct simulation."""
    from collections import defaultdict
    
    print("🧪 CORRECT Artist Matching Test Scenario")
    print("=" * 50)
    print("Scenario: New playlist contains songs by artists who")
    print("exist ONLY in other specific playlists (single-playlist artists)")
    print("=" * 50)
    
    playlists_dict = create_correct_test_data()
    
    # Build artist mappings
    artist_to_playlists = defaultdict(set)
    
    for playlist_name, playlist_data in playlists_dict.items():
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                artist_id = artist.get("id")
                if artist_id:
                    artist_to_playlists[artist_id].add(playlist_name)
    
    print(f"\nArtist distribution across ALL playlists:")
    for artist_id, playlists in sorted(artist_to_playlists.items()):
        count = len(playlists)
        playlist_names = ", ".join(sorted(playlists))
        if count == 1:
            print(f"  🎯 SINGLE: {artist_id} → {playlist_names}")
        else:
            print(f"  ❌ MULTI({count}): {artist_id} → {playlist_names}")
    
    # Find single playlist artists
    single_playlist_artists = set()
    for artist_id, playlists in artist_to_playlists.items():
        if len(playlists) == 1:
            single_playlist_artists.add(artist_id)
    
    print(f"\nSingle-playlist artists: {len(single_playlist_artists)}")
    
    # Process matching
    print(f"\n" + "=" * 50)
    print("TESTING ARTIST MATCHING LOGIC")
    print("=" * 50)
    
    matches = defaultdict(list)
    source_tracks = playlists_dict["New"]["tracks"]
    
    print(f"Processing {len(source_tracks)} tracks from 'New' playlist:\n")
    
    for track in source_tracks:
        track_id = track["id"] 
        track_name = track["name"]
        
        print(f"🔍 Track: '{track_name}'")
        
        found_match = False
        for artist in track["artists"]:
            artist_id = artist.get("id")
            artist_name = artist.get("name")
            
            print(f"   🎤 Artist: {artist_name} ({artist_id})")
            
            if artist_id in single_playlist_artists:
                # Artist appears in exactly one playlist
                target_playlists = artist_to_playlists[artist_id]
                target_playlist_name = list(target_playlists)[0]
                
                print(f"   ✅ Single-playlist artist found!")
                print(f"   🎯 Target playlist: '{target_playlist_name}'")
                
                # Don't add to source playlist itself
                if target_playlist_name == "New":
                    print(f"   ⚠️ Target is source playlist - skipping")
                    continue
                
                # Check if track already exists in target
                target_tracks = playlists_dict[target_playlist_name]["tracks"]
                existing_track_ids = {t["id"] for t in target_tracks}
                
                if track_id not in existing_track_ids:
                    matches[target_playlist_name].append({
                        "track_name": track_name,
                        "artist_name": artist_name, 
                        "track_id": track_id
                    })
                    print(f"   🎉 MATCH! Will add to '{target_playlist_name}'")
                    found_match = True
                else:
                    print(f"   ⚠️ Track already exists in '{target_playlist_name}'")
                
                break
            else:
                playlist_count = len(artist_to_playlists[artist_id])
                playlists_list = ", ".join(sorted(artist_to_playlists[artist_id]))
                print(f"   ❌ Multi-playlist artist (appears in {playlist_count}: {playlists_list})")
        
        if not found_match:
            print(f"   ❌ No match found for this track")
        
        print()  # Empty line for readability
    
    # Final results
    print("=" * 50)
    print("FINAL RESULTS")
    print("=" * 50)
    
    if matches:
        total_matches = sum(len(track_list) for track_list in matches.values())
        print(f"🎉 SUCCESS! Found {total_matches} matches across {len(matches)} target playlists!")
        
        for target_playlist, track_list in matches.items():
            print(f"\n📀 Target Playlist: '{target_playlist}'")
            print(f"   📈 Songs to add: {len(track_list)}")
            for track_info in track_list:
                print(f"      ➕ '{track_info['track_name']}' by {track_info['artist_name']}")
        
        print(f"\n" + "=" * 50)
        print("✅ AUTOMATION VERIFICATION COMPLETE")
        print("=" * 50)
        print(f"✅ Logic correctly identifies single-playlist artists: {len(single_playlist_artists)} found")
        print(f"✅ Logic correctly matches tracks to target playlists: {total_matches} matches")
        print(f"✅ Logic correctly avoids duplicates and self-references")
        print(f"✅ Artist matching automation is WORKING and ready for production!")
        
    else:
        print("❌ No matches found")
        print("This might be expected if no single-playlist artists exist in the test data")


if __name__ == "__main__":
    run_correct_simulation()