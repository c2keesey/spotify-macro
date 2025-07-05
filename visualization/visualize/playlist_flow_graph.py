"""
Playlist flow graph visualization using cached relationship data.

Generates visual representations of playlist flow relationships without requiring
additional API calls, using the cached metadata from playlist flow automation.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Optional visualization dependencies
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False

from common.config import CURRENT_ENV
from common.playlist_cache import create_playlist_cache


def load_flow_graph_from_cache() -> Optional[Tuple[Dict, Dict, Dict]]:
    """
    Load playlist flow graph from cache.
    
    Returns:
        Tuple of (playlists, parent_to_children, child_to_parents) or None if cache invalid
    """
    cache = create_playlist_cache()
    cache_stats = cache.get_cache_stats()
    
    if cache_stats['status'] != 'valid':
        print(f"Cache not valid: {cache_stats}")
        return None
    
    playlists = cache.get_cached_playlists()
    relationships = cache.get_cached_relationships()
    
    if playlists is None or relationships is None:
        print("No cached data available")
        return None
    
    parent_to_children, child_to_parents = relationships
    
    print(f"Loaded flow graph from cache:")
    print(f"  - {len(playlists)} playlists")
    print(f"  - {len(parent_to_children)} parent relationships")
    print(f"  - Cache age: {cache_stats['age_hours']:.1f} hours")
    
    return playlists, parent_to_children, child_to_parents


def export_graph_data(output_path: str = "playlist_flow_graph.json") -> bool:
    """
    Export flow graph data to JSON for external visualization tools.
    
    Args:
        output_path: Path to output JSON file
        
    Returns:
        True if successful, False otherwise
    """
    graph_data = load_flow_graph_from_cache()
    if not graph_data:
        return False
    
    playlists, parent_to_children, child_to_parents = graph_data
    
    # Create nodes and edges for standard graph formats
    nodes = []
    edges = []
    
    # Add nodes
    for playlist_id, data in playlists.items():
        node = {
            'id': playlist_id,
            'name': data['name'],
            'parent_chars': data['parent_chars'],
            'child_chars': data['child_chars'],
            'track_count': data.get('track_count'),
            'type': 'parent_only' if data['parent_chars'] and not data['child_chars'] else
                   'child_only' if data['child_chars'] and not data['parent_chars'] else
                   'both' if data['parent_chars'] and data['child_chars'] else
                   'normal'
        }
        nodes.append(node)
    
    # Add edges (child -> parent direction)
    for parent_id, child_ids in parent_to_children.items():
        for child_id in child_ids:
            edge = {
                'source': child_id,
                'target': parent_id,
                'source_name': playlists[child_id]['name'],
                'target_name': playlists[parent_id]['name'],
                'type': 'flow'
            }
            edges.append(edge)
    
    # Export data
    # Get cache timestamp
    cache = create_playlist_cache()
    
    export_data = {
        'metadata': {
            'total_playlists': len(playlists),
            'flow_relationships': len(edges),
            'environment': CURRENT_ENV,
            'export_timestamp': cache.cache_data.get('timestamp', 0)
        },
        'nodes': nodes,
        'edges': edges,
        'raw_relationships': {
            'parent_to_children': parent_to_children,
            'child_to_parents': child_to_parents
        }
    }
    
    try:
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported flow graph data to {output_path}")
        print(f"  - {len(nodes)} nodes")
        print(f"  - {len(edges)} edges")
        return True
        
    except Exception as e:
        print(f"Failed to export graph data: {e}")
        return False


def create_networkx_graph() -> Optional['nx.DiGraph']:
    """
    Create a NetworkX directed graph from cached flow data.
    
    Returns:
        NetworkX DiGraph or None if cache invalid or networkx not available
    """
    if not HAS_VISUALIZATION:
        print("NetworkX not available. Install with: uv add networkx matplotlib")
        return None
    
    graph_data = load_flow_graph_from_cache()
    if not graph_data:
        return None
    
    playlists, parent_to_children, child_to_parents = graph_data
    
    # Create directed graph (child -> parent)
    G = nx.DiGraph()
    
    # Add nodes with attributes
    for playlist_id, data in playlists.items():
        G.add_node(playlist_id, **data)
    
    # Add edges (child -> parent)
    for parent_id, child_ids in parent_to_children.items():
        for child_id in child_ids:
            G.add_edge(child_id, parent_id)
    
    print(f"Created NetworkX graph: {len(G.nodes)} nodes, {len(G.edges)} edges")
    return G


def visualize_flow_graph(output_path: str = "playlist_flow_visualization.png", 
                        figsize: Tuple[int, int] = (16, 12),
                        show_labels: bool = True) -> bool:
    """
    Create a visual representation of the playlist flow graph.
    
    Args:
        output_path: Path to save the visualization
        figsize: Figure size (width, height)
        show_labels: Whether to show playlist names as labels
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_VISUALIZATION:
        print("Visualization libraries not available.")
        print("Install with: uv add networkx matplotlib")
        return False
    
    G = create_networkx_graph()
    if not G:
        return False
    
    plt.figure(figsize=figsize)
    
    # Position nodes using spring layout for better visualization
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Color nodes by type
    node_colors = []
    for node_id in G.nodes():
        data = G.nodes[node_id]
        if data['parent_chars'] and data['child_chars']:
            node_colors.append('orange')  # Both parent and child
        elif data['parent_chars']:
            node_colors.append('lightblue')  # Parent only
        elif data['child_chars']:
            node_colors.append('lightgreen')  # Child only
        else:
            node_colors.append('lightgray')  # No flow characters
    
    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1000, alpha=0.8)
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, alpha=0.6)
    
    if show_labels:
        # Create shorter labels for readability
        labels = {}
        for node_id in G.nodes():
            name = G.nodes[node_id]['name']
            # Truncate long names
            labels[node_id] = name[:20] + "..." if len(name) > 20 else name
        
        nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    # Add legend
    legend_elements = [
        mpatches.Patch(color='lightblue', label='Parent Only'),
        mpatches.Patch(color='lightgreen', label='Child Only'),
        mpatches.Patch(color='orange', label='Parent & Child'),
        mpatches.Patch(color='lightgray', label='No Flow')
    ]
    plt.legend(handles=legend_elements, loc='upper left')
    
    plt.title(f"Spotify Playlist Flow Graph ({CURRENT_ENV} environment)\n"
              f"{len(G.nodes)} playlists, {len(G.edges)} flow relationships")
    plt.axis('off')
    
    try:
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved visualization to {output_path}")
        return True
        
    except Exception as e:
        print(f"Failed to save visualization: {e}")
        return False


def print_flow_summary():
    """Print a text summary of the flow graph."""
    graph_data = load_flow_graph_from_cache()
    if not graph_data:
        return
    
    playlists, parent_to_children, child_to_parents = graph_data
    
    print("\n=== PLAYLIST FLOW SUMMARY ===")
    
    # Find different types of playlists
    parents_only = []
    children_only = []
    both = []
    no_flow = []
    
    for playlist_id, data in playlists.items():
        name = data['name']
        if data['parent_chars'] and data['child_chars']:
            both.append(f"  {name} (chars: {data['parent_chars']} -> {data['child_chars']})")
        elif data['parent_chars']:
            parents_only.append(f"  {name} (chars: {data['parent_chars']})")
        elif data['child_chars']:
            children_only.append(f"  {name} (chars: {data['child_chars']})")
        else:
            no_flow.append(f"  {name}")
    
    if parents_only:
        print(f"\nParent Playlists ({len(parents_only)}):")
        for item in parents_only[:10]:  # Show first 10
            print(item)
        if len(parents_only) > 10:
            print(f"  ... and {len(parents_only) - 10} more")
    
    if children_only:
        print(f"\nChild Playlists ({len(children_only)}):")
        for item in children_only[:10]:
            print(item)
        if len(children_only) > 10:
            print(f"  ... and {len(children_only) - 10} more")
    
    if both:
        print(f"\nDual-Role Playlists ({len(both)}):")
        for item in both:
            print(item)
    
    # Show some example flows
    print(f"\nExample Flow Relationships:")
    count = 0
    for parent_id, child_ids in parent_to_children.items():
        if count >= 5:  # Show first 5
            break
        parent_name = playlists[parent_id]['name']
        child_names = [playlists[child_id]['name'] for child_id in child_ids]
        print(f"  {parent_name} ← {', '.join(child_names)}")
        count += 1
    
    if len(parent_to_children) > 5:
        print(f"  ... and {len(parent_to_children) - 5} more relationships")


def main():
    """Main function for command-line usage."""
    print("Playlist Flow Graph Visualization")
    print("=================================")
    
    # Print summary
    print_flow_summary()
    
    # Export JSON data
    print("\nExporting graph data...")
    success = export_graph_data()
    if not success:
        print("No data to export - cache is empty. Run playlist flow automation first.")
    
    # Create visualization if possible
    if HAS_VISUALIZATION:
        print("\nCreating visualization...")
        visualize_flow_graph()
    else:
        print("\nVisualization libraries not installed.")
        print("To create visual graphs, install: uv add networkx matplotlib")


if __name__ == "__main__":
    main()