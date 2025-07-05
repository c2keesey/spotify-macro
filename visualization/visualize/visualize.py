import csv
import json
import os

import matplotlib.pyplot as plt
import networkx as nx

# Define a distinct color palette
PLAYLIST_COLOR = "skyblue"
GENRE_COLOR = "lightgreen"
EDGE_COLOR = "gray"
FONT_COLOR = "black"


def load_playlist_data(file_path: str) -> dict | None:
    """
    Loads playlist data from a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        A dictionary containing the playlist data, or None if an error occurs.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} is not a valid JSON file.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None


def build_graph_from_data(data: dict) -> nx.Graph:
    """
    Builds a NetworkX graph from the playlist data.

    Args:
        data: A dictionary where keys are playlist IDs and values are dicts
              containing 'playlist_name' and 'genre_song_counts'.

    Returns:
        A NetworkX graph where nodes are playlists and genres, and edges
        represent the number of songs of a genre in a playlist.
    """
    G = nx.Graph()

    # Store total songs for playlists and genres to potentially size nodes later
    playlist_total_songs = {}
    genre_total_songs = {}

    for playlist_id, details in data.items():
        playlist_name = details.get("playlist_name", playlist_id)

        # Add playlist node
        # Prefix to avoid collision if a playlist name is same as a genre name
        node_playlist_name = f"P: {playlist_name}"
        G.add_node(
            node_playlist_name, type="playlist", name=playlist_name, id=playlist_id
        )

        current_playlist_total_songs = 0
        genre_song_counts = details.get("genre_song_counts", {})
        for genre, count in genre_song_counts.items():
            if count <= 0:  # Skip genres with no songs or invalid counts
                continue

            # Add genre node
            node_genre_name = f"G: {genre}"  # Prefix for clarity
            if not G.has_node(node_genre_name):
                G.add_node(node_genre_name, type="genre", name=genre)

            # Add edge between playlist and genre
            G.add_edge(node_playlist_name, node_genre_name, weight=count)

            current_playlist_total_songs += count
            genre_total_songs[node_genre_name] = (
                genre_total_songs.get(node_genre_name, 0) + count
            )

        playlist_total_songs[node_playlist_name] = current_playlist_total_songs

    # Add song counts as attributes to nodes for potential use in sizing
    for node, total_songs in playlist_total_songs.items():
        if G.has_node(node):
            G.nodes[node]["total_songs"] = total_songs
    for node, total_songs in genre_total_songs.items():
        if G.has_node(node):
            G.nodes[node]["total_songs"] = total_songs

    return G


def export_graph_to_csvs(
    graph: nx.Graph,
    output_dir: str = ".",
    nodes_filename: str = "nodes.csv",
    edges_filename: str = "edges.csv",
) -> None:
    """
    Exports graph nodes and edges to CSV files.

    Args:
        graph: The NetworkX graph to export.
        output_dir: The directory to save the CSV files in.
        nodes_filename: Filename for the nodes CSV.
        edges_filename: Filename for the edges CSV.
    """
    if not graph.nodes:
        print("Graph is empty. Nothing to export.")
        return

    nodes_filepath = os.path.join(output_dir, nodes_filename)
    edges_filepath = os.path.join(output_dir, edges_filename)

    # Export Nodes
    with open(nodes_filepath, "w", newline="", encoding="utf-8") as f_nodes:
        writer = csv.writer(f_nodes)
        # Gephi specific headers: Id, Label, Type, plus custom attributes
        header = ["Id", "Label", "Type", "TotalSongs"]
        writer.writerow(header)
        for node_id, attrs in graph.nodes(data=True):
            label = attrs.get("name", node_id)  # Use the clean name for Label
            node_type = attrs.get("type", "Unknown")
            total_songs = attrs.get("total_songs", 0)
            writer.writerow([node_id, label, node_type, total_songs])
    print(f"Nodes exported to {nodes_filepath}")

    # Export Edges
    with open(edges_filepath, "w", newline="", encoding="utf-8") as f_edges:
        writer = csv.writer(f_edges)
        # Gephi specific headers: Source, Target, Type, Weight (plus other attributes if any)
        header = ["Source", "Target", "Type", "Weight"]
        writer.writerow(header)
        for source, target, attrs in graph.edges(data=True):
            weight = attrs.get("weight", 0)
            # For undirected graphs, Gephi expects 'Undirected' or 'Directed'
            edge_type = "Undirected"
            writer.writerow([source, target, edge_type, weight])
    print(f"Edges exported to {edges_filepath}")


def draw_playlist_genre_graph(
    graph: nx.Graph,
    output_path: str | None = "playlist_genre_network.png",
    k_layout: float = 0.3,
) -> None:
    """
    Draws the playlist-genre graph and saves it to a file or displays it.

    Args:
        graph: The NetworkX graph to draw.
        output_path: Path to save the output image. If None, displays the plot.
                     Defaults to "playlist_genre_network.png".
        k_layout: Optimal distance between nodes for the spring layout.
                  Adjust this value to spread out or compact the graph.
    """
    if not graph.nodes:
        print("Graph is empty. Nothing to draw.")
        return

    plt.figure(figsize=(20, 20))  # Increased figure size for better readability

    # Use a spring layout; k adjusts the optimal distance between nodes
    # iterations can be increased for a more stable layout, but adds computation time
    pos = nx.spring_layout(graph, k=k_layout, iterations=50, seed=42)

    playlist_nodes = [
        n for n, d in graph.nodes(data=True) if d.get("type") == "playlist"
    ]
    genre_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "genre"]

    # Determine node sizes (optional: could be fixed or based on 'total_songs')
    # Simple fixed sizes for now, can be enhanced
    playlist_node_sizes = [
        graph.nodes[n].get("total_songs", 10) * 5 + 500 for n in playlist_nodes
    ]  # Basic scaling
    genre_node_sizes = [
        graph.nodes[n].get("total_songs", 1) * 20 + 200 for n in genre_nodes
    ]  # Basic scaling for genres

    # Draw nodes
    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=playlist_nodes,
        node_color=PLAYLIST_COLOR,
        node_size=playlist_node_sizes,
        label="Playlists",
        alpha=0.9,
    )
    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=genre_nodes,
        node_color=GENRE_COLOR,
        node_size=genre_node_sizes,
        label="Genres",
        alpha=0.9,
    )

    # Draw edges with varying widths
    edges = graph.edges(data=True)
    if edges:
        all_weights = [d["weight"] for _, _, d in edges if d["weight"] > 0]
        if all_weights:
            min_w, max_w = min(all_weights), max(all_weights)
            if min_w == max_w:  # All weights are same or only one edge
                edge_widths = [1.0] * len(edges)
            else:
                # Scale weights to a visible range (e.g., 0.5 to 8.0)
                edge_widths = [
                    0.5 + (d["weight"] - min_w) * (8.0 - 0.5) / (max_w - min_w)
                    if d["weight"] > 0
                    else 0.1
                    for _, _, d in edges
                ]
        else:  # No positive weights
            edge_widths = [0.5] * len(edges)  # Default width if no weights or all zero

        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=edges,
            width=edge_widths,
            alpha=0.4,
            edge_color=EDGE_COLOR,
        )
    else:  # No edges
        nx.draw_networkx_edges(graph, pos, width=1.0, alpha=0.4, edge_color=EDGE_COLOR)

    # Draw labels: use original names stored in node attributes for cleaner labels
    labels = {n: d.get("name", n) for n, d in graph.nodes(data=True)}
    nx.draw_networkx_labels(
        graph, pos, labels=labels, font_size=9, font_color=FONT_COLOR
    )

    plt.title("Playlist-Genre Relationship Network", fontsize=20)
    plt.xlabel(f"Nodes: {len(graph.nodes())}, Edges: {len(graph.edges())}", fontsize=12)
    plt.axis("off")
    plt.legend(scatterpoints=1, loc="upper right", fontsize=12)
    plt.tight_layout()  # Adjusts plot to prevent labels from being cut off

    if output_path:
        try:
            # Ensure the directory for the output path exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            print(f"Graph saved to {output_path}")
        except Exception as e:
            print(f"Error saving graph to {output_path}: {e}")
            plt.show()  # Show plot if saving failed
    else:
        plt.show()


def main():
    """
    Main function to load data, build graph, and visualize it.
    """
    # Path to the data file, relative to the workspace root
    # The user provided _data/playlist_to_genres.json
    # Assuming this script visualize.py is in visualize/ folder,
    # and _data is at the root.
    data_file = "/Users/c2k/Projects/spotify-macro/_data/playlist_to_genres.json"

    # Output directory for CSVs and image (e.g., current script's directory)
    # By default, files will be saved where the script is run from.
    # If visualize.py is in visualize/, files go to visualize/
    output_directory = "."  # Can be changed to a subfolder like "output_data"
    image_output_file = os.path.join(output_directory, "playlist_genre_network.png")
    nodes_csv_file = os.path.join(output_directory, "nodes.csv")
    edges_csv_file = os.path.join(output_directory, "edges.csv")

    playlist_data = load_playlist_data(data_file)

    if playlist_data:
        graph = build_graph_from_data(playlist_data)
        if graph and graph.nodes:
            # Adjust k_layout based on graph density. Smaller k for denser graphs if nodes overlap too much.
            # Larger k to spread out sparse graphs.
            # Number of nodes can be a simple heuristic:
            num_nodes = len(graph.nodes())
            k_val = 0.8 if num_nodes < 50 else 0.5 if num_nodes < 150 else 0.3

            print(
                f"Generated graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges."
            )
            print(f"Using k={k_val} for spring layout.")
            draw_playlist_genre_graph(
                graph, output_path=image_output_file, k_layout=k_val
            )
            export_graph_to_csvs(
                graph,
                output_dir=output_directory,
                nodes_filename="nodes.csv",
                edges_filename="edges.csv",
            )
        else:
            print("Failed to build a graph or the graph is empty.")
    else:
        print("Failed to load playlist data.")


if __name__ == "__main__":
    main()
    # Example of how to use the functions if imported as a module:
    # data = load_playlist_data("path/to/your/playlist_to_genres.json")
    # if data:
    #   g = build_graph_from_data(data)
    #   draw_playlist_genre_graph(g, "my_custom_graph.png")
