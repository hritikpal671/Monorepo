"""
Graph builder module to create knowledge graph using local SQLite and NetworkX
"""

import sqlite3
import json
import networkx as nx
import pandas as pd
from typing import List, Dict, Any, Optional
import re
from pyvis.network import Network


class GraphBuilder:
    """Build and manage knowledge graphs locally using SQLite and NetworkX"""
    
    def __init__(self, db_path: str = "graphrag_local.db"):
        """
        Initialize SQLite connection and in-memory NetworkX graph
        
        Args:
            db_path: Path to local SQLite database file
        """
        self.db_path = db_path
        self.nx_graph = nx.MultiDiGraph()
        
        self._init_db()
        self._load_graph_into_memory()
        print(f"[OK] Connected to local SQLite DB: {self.db_path}")
    
    def _init_db(self):
        """Create the necessary tables and indexes in SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    labels TEXT,
                    value TEXT,
                    column TEXT,
                    row_index INTEGER,
                    group_id TEXT,
                    properties TEXT
                )
            """)
            # Edges table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT,
                    target TEXT,
                    type TEXT,
                    properties TEXT,
                    FOREIGN KEY(source) REFERENCES nodes(id),
                    FOREIGN KEY(target) REFERENCES nodes(id)
                )
            """)
            # Indexes for fast searching
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_value ON nodes(value)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_group ON nodes(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_labels ON nodes(labels)")
            conn.commit()
            
    def _load_graph_into_memory(self):
        """Load SQLite edges into NetworkX for fast traversal during query time"""
        self.nx_graph.clear()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, labels, value, column, row_index, group_id, properties FROM nodes")
            for n_id, labels, val, col, r_idx, g_id, props_json in cursor.fetchall():
                props = json.loads(props_json) if props_json else {}
                self.nx_graph.add_node(
                    n_id, labels=labels, value=val, column=col, 
                    row_index=r_idx, group_id=g_id, **props
                )
                
            cursor.execute("SELECT source, target, type, properties FROM edges")
            for source, target, edge_type, props_json in cursor.fetchall():
                props = json.loads(props_json) if props_json else {}
                self.nx_graph.add_edge(source, target, type=edge_type, **props)
    
    def close(self):
        """Clean up resources (no active driver to close for SQLite)"""
        pass
    
    def clear_graph(self):
        """Clear all nodes and relationships from the database and memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM edges")
            cursor.execute("DELETE FROM nodes")
            conn.commit()
        self.nx_graph.clear()
        print("[OK] Local graph cleared")
    
    def _infer_primary_key_column(self, data: pd.DataFrame) -> Any:
        """Pick the best primary key column from the dataset."""
        if data.empty or len(data.columns) == 0:
            raise ValueError("Cannot build a graph from an empty DataFrame")

        non_null_unique_columns = [
            col for col in data.columns
            if data[col].notna().all() and data[col].astype(str).is_unique
        ]

        if non_null_unique_columns:
            id_like_columns = [
                col for col in non_null_unique_columns
                if self._looks_like_identifier(str(col))
            ]
            return id_like_columns[0] if id_like_columns else non_null_unique_columns[0]

        return data.columns[0]

    def _looks_like_identifier(self, column_name: str) -> bool:
        """Return whether a column name appears to be an identifier."""
        normalized = re.sub(r"[^a-z0-9]+", "_", column_name.lower()).strip("_")
        return (
            normalized in {"id", "key", "pk", "primary_key", "identifier"}
            or normalized.endswith("_id")
            or normalized.endswith("_key")
        )

    def _cell_value(self, value: Any) -> Optional[str]:
        if pd.isna(value):
            return None
        return str(value)

    def _node_id(self, row_index: int, column: str, value: str, is_primary: bool) -> str:
        if is_primary:
            return f"pk::{column}::{value}::row::{row_index}"
        return f"cell::row::{row_index}::column::{column}"

    def _column_node_id(self, column: str) -> str:
        return f"column::{column}"

    def _select_columns(self, data: pd.DataFrame, selected_columns: Optional[List[str]]) -> pd.DataFrame:
        """Return a DataFrame restricted to the user-selected graph columns."""
        data = data.copy()
        data.columns = [str(column) for column in data.columns]

        if selected_columns is None:
            return data

        normalized_columns = [str(column) for column in selected_columns if str(column).strip()]
        if not normalized_columns:
            raise ValueError("Select at least one column to build the graph")

        missing_columns = [column for column in normalized_columns if column not in data.columns]
        if missing_columns:
            raise ValueError(f"Selected columns not found in data: {', '.join(missing_columns)}")

        deduped_columns = list(dict.fromkeys(normalized_columns))
        return data.loc[:, deduped_columns]

    def build_from_dataframe(
        self,
        data: pd.DataFrame,
        clear_existing: bool = True,
        primary_key_column: Optional[str] = None,
        selected_columns: Optional[List[str]] = None,
    ):
        """Build a graph from only the selected columns and persist it to SQLite."""
        if clear_existing:
            self.clear_graph()
            
        data = self._select_columns(data, selected_columns)

        if data.empty:
            print("[WARN] DataFrame is empty; no graph nodes were created")
            return

        print(f"Building local graph from DataFrame with shape {data.shape}...")
        print(f"Graph column scope: {', '.join(str(column) for column in data.columns)}")

        if primary_key_column and primary_key_column not in data.columns:
            raise ValueError("Primary key column must be one of the selected graph columns")

        primary_key_column = primary_key_column or self._infer_primary_key_column(data)
        
        nodes_to_insert = []
        edges_to_insert = []
        all_row_ids = []
        value_to_rows = {}
        selected_column_names = [str(column) for column in data.columns]

        # Column-level graph schema: every selected column is connected to every
        # other selected column in both directions.
        for column in selected_column_names:
            column_id = self._column_node_id(column)
            column_props = json.dumps({
                "selected_for_graph": True,
                "name": column,
            })
            nodes_to_insert.append((column_id, "Column:GraphColumn", column, column, None, None, column_props))

        for left_index, left_column in enumerate(selected_column_names):
            for right_column in selected_column_names[left_index + 1:]:
                rel_props = json.dumps({"relationship": "bidirectional_column_scope"})
                edges_to_insert.extend([
                    (self._column_node_id(left_column), self._column_node_id(right_column), "RELATED_COLUMN", rel_props),
                    (self._column_node_id(right_column), self._column_node_id(left_column), "RELATED_COLUMN", rel_props),
                ])

        for row_index, (_, row) in enumerate(data.iterrows()):
            row_id = f"row_{row_index}"
            all_row_ids.append(row_id)
            primary_value = self._cell_value(row[primary_key_column]) or row_id
            primary_node_id = self._node_id(row_index, primary_key_column, primary_value, True)

            # 1. Create RowGroup Community Node
            row_props = json.dumps({
                "primary_key_column": primary_key_column,
                "primary_key_value": primary_value,
                "selected_columns": selected_column_names,
                "name": primary_value
            })
            nodes_to_insert.append((row_id, "DataRow:RowGroup:Community", primary_value, primary_key_column, row_index, row_id, row_props))

            # 2. Create Primary Entity Node
            p_props = json.dumps({"is_primary_key": True, "primary_key_column": primary_key_column, "primary_key_value": primary_value})
            nodes_to_insert.append((primary_node_id, "Cell:PrimaryEntity", primary_value, primary_key_column, row_index, row_id, p_props))

            # RowGroup <-> PrimaryEntity Edges
            edges_to_insert.extend([
                (row_id, primary_node_id, "HAS_PRIMARY_KEY", "{}"),
                (primary_node_id, row_id, "PRIMARY_KEY_OF", "{}"),
                (row_id, primary_node_id, "GROUP_HAS_CELL", json.dumps({"column": primary_key_column})),
                (primary_node_id, row_id, "CELL_IN_GROUP", json.dumps({"column": primary_key_column})),
                (self._column_node_id(str(primary_key_column)), primary_node_id, "COLUMN_HAS_VALUE", json.dumps({"column": str(primary_key_column)})),
                (primary_node_id, self._column_node_id(str(primary_key_column)), "VALUE_IN_COLUMN", json.dumps({"column": str(primary_key_column)}))
            ])

            cell_nodes = [{"id": primary_node_id, "column": primary_key_column, "value": primary_value}]
            value_to_rows.setdefault(str(primary_value).lower(), set()).add(row_id)
            
            # 3. Create Cell Nodes
            for col, value in row.items():
                val_str = self._cell_value(value)
                if val_str is None or col == primary_key_column:
                    continue

                cell_id = self._node_id(row_index, str(col), val_str, False)
                cell_nodes.append({"id": cell_id, "column": str(col), "value": val_str})
                value_to_rows.setdefault(val_str.lower(), set()).add(row_id)
                
                c_props = json.dumps({"is_primary_key": False, "primary_key_column": primary_key_column, "primary_key_value": primary_value})
                nodes_to_insert.append((cell_id, "Cell:ColumnValue", val_str, str(col), row_index, row_id, c_props))
                
                # PrimaryEntity <-> Cell Edges
                edges_to_insert.extend([
                    (primary_node_id, cell_id, "HAS_FIELD", json.dumps({"column": str(col), "row_index": row_index})),
                    (cell_id, primary_node_id, "FIELD_OF", json.dumps({"column": str(col), "row_index": row_index})),
                    (row_id, cell_id, "GROUP_HAS_CELL", json.dumps({"column": str(col)})),
                    (cell_id, row_id, "CELL_IN_GROUP", json.dumps({"column": str(col)})),
                    (self._column_node_id(str(col)), cell_id, "COLUMN_HAS_VALUE", json.dumps({"column": str(col)})),
                    (cell_id, self._column_node_id(str(col)), "VALUE_IN_COLUMN", json.dumps({"column": str(col)}))
                ])

            # 4. Pairwise Relationships
            for left_index, left_cell in enumerate(cell_nodes):
                for right_cell in cell_nodes[left_index + 1:]:
                    rel_props = json.dumps({"row_id": row_id})
                    edges_to_insert.extend([
                        (left_cell["id"], right_cell["id"], "RELATED_IN_ROW", rel_props),
                        (right_cell["id"], left_cell["id"], "RELATED_IN_ROW", rel_props)
                    ])

        # For each shared selected-column value, connect rows that share it.
        connected_pairs = set()
        for val, row_ids_with_val in value_to_rows.items():
            row_ids_with_val = sorted(row_ids_with_val)
            if len(row_ids_with_val) > 1:
                for i, row1 in enumerate(row_ids_with_val):
                    for row2 in row_ids_with_val[i + 1:]:
                        pair = tuple(sorted([row1, row2]))
                        if pair not in connected_pairs:
                            connected_pairs.add(pair)
                            # Create bidirectional edges for rows sharing values
                            edges_to_insert.extend([
                                (pair[0], pair[1], "SHARES_VALUE", json.dumps({"shared_value": val})),
                                (pair[1], pair[0], "SHARES_VALUE", json.dumps({"shared_value": val}))
                            ])

        # Batch insert to SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany("INSERT OR IGNORE INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)", nodes_to_insert)
            cursor.executemany("INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?)", edges_to_insert)
            conn.commit()

        self._load_graph_into_memory()
        print(f"[OK] Created {len(data)} row communities using primary key '{primary_key_column}'")
        print(f"[OK] Graph built from {len(selected_column_names)} selected columns")
        print(f"[OK] Connected {len(connected_pairs)} row pairs via shared values")
        audit = self.audit_bidirectional_edges()
        if audit["missing_reverse_edges"]:
            print(f"[WARN] Missing reverse edges detected: {audit['missing_reverse_edges']}")
        else:
            print(f"[OK] Verified bidirectional directions for {audit['checked_edges']} graph relationships")

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the current graph"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM edges")
            total_relationships = cursor.fetchone()[0]
            
            cursor.execute("SELECT DISTINCT labels FROM nodes LIMIT 10")
            labels = [{"labels": r[0]} for r in cursor.fetchall()]

        return {
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "node_labels": labels
        }

    def audit_bidirectional_edges(self) -> Dict[str, Any]:
        """Verify graph relationships have the expected reverse direction."""
        same_type_reverse = {"RELATED_COLUMN", "RELATED_IN_ROW", "SHARES_VALUE"}
        semantic_reverse = {
            "HAS_PRIMARY_KEY": "PRIMARY_KEY_OF",
            "PRIMARY_KEY_OF": "HAS_PRIMARY_KEY",
            "GROUP_HAS_CELL": "CELL_IN_GROUP",
            "CELL_IN_GROUP": "GROUP_HAS_CELL",
            "COLUMN_HAS_VALUE": "VALUE_IN_COLUMN",
            "VALUE_IN_COLUMN": "COLUMN_HAS_VALUE",
            "HAS_FIELD": "FIELD_OF",
            "FIELD_OF": "HAS_FIELD",
        }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source, target, type FROM edges")
            edges = cursor.fetchall()

        edge_set = {(source, target, edge_type) for source, target, edge_type in edges}
        missing_reverse_edges = []

        for source, target, edge_type in edges:
            reverse_type = edge_type if edge_type in same_type_reverse else semantic_reverse.get(edge_type)
            if not reverse_type:
                continue

            if (target, source, reverse_type) not in edge_set:
                missing_reverse_edges.append({
                    "source": source,
                    "target": target,
                    "type": edge_type,
                    "expected_reverse_type": reverse_type,
                })

        return {
            "checked_edges": len(edges),
            "missing_reverse_edges": missing_reverse_edges,
        }
        
    def search_entity(self, entity_value: str, limit: int = 100000) -> List[Dict]:
        """Search SQLite for an entity matching the value"""
        entity_value = str(entity_value).strip().lower()
        if not entity_value:
            return []

        allow_contains = len(entity_value) > 2
        
        query = """
            SELECT id, value, labels, column, row_index, group_id, properties 
            FROM nodes 
            WHERE LOWER(value) = ? OR LOWER(id) = ? 
        """
        params = [entity_value, entity_value]
        
        if allow_contains:
            query += " OR LOWER(value) LIKE ? OR LOWER(id) LIKE ?"
            params.extend([f"%{entity_value}%", f"%{entity_value}%"])
            
        query += f" LIMIT {max(1, limit)}"
        
        results = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for r in cursor.fetchall():
                props = json.loads(r[6]) if r[6] else {}
                results.append({
                    "value": r[1],
                    "labels": r[2].split(':'),
                    "column": r[3],
                    "row_index": r[4],
                    "group_id": r[5],
                    "primary_key_column": props.get("primary_key_column"),
                    "primary_key_value": props.get("primary_key_value")
                })
        return results

    def search_rows_by_any_criteria(self, search_values: List[str], limit: int = 100000) -> List[Dict]:
        """Find all RowGroups that contain ANY of the search values - ranked by relevance"""
        search_values = [str(v).strip().lower() for v in search_values if str(v).strip()]
        if not search_values:
            return []

        # Build a query that finds rows containing ANY of the search terms, ranked by match count
        partial_query = """
            SELECT DISTINCT group_id, COUNT(*) as match_count
            FROM nodes
            WHERE group_id IS NOT NULL AND group_id != ''
        """
        partial_params = []
        
        where_conditions = []
        for val in search_values:
            if len(val) > 2:
                where_conditions.append("(LOWER(value) = ? OR LOWER(value) LIKE ?)")
                partial_params.extend([val, f"%{val}%"])
            else:
                where_conditions.append("(LOWER(value) = ?)")
                partial_params.append(val)
        
        if where_conditions:
            partial_query += " AND (" + " OR ".join(where_conditions) + ")"
        
        partial_query += " GROUP BY group_id ORDER BY match_count DESC LIMIT ?"
        partial_params.append(limit)
        
        valid_group_ids = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(partial_query, partial_params)
            valid_group_ids = [row[0] for row in cursor.fetchall() if row[0] is not None]
        
        # Fetch the context for these groups (ranked by relevance)
        return [self._get_row_context_by_group(gid) for gid in valid_group_ids[:limit]]

    def search_rows_matching_all_criteria(self, search_values: List[str], limit: int = 100000) -> List[Dict]:
        """Find RowGroups that contain ALL search values using SQLite Intersects"""
        search_values = [str(v).strip().lower() for v in search_values if str(v).strip()]
        if not search_values:
            return []

        intersect_queries = []
        params = []
        
        for val in search_values:
            if len(val) > 2:
                intersect_queries.append("SELECT group_id FROM nodes WHERE LOWER(value) = ? OR LOWER(value) LIKE ?")
                params.extend([val, f"%{val}%"])
            else:
                intersect_queries.append("SELECT group_id FROM nodes WHERE LOWER(value) = ?")
                params.append(val)
                
        final_query = " INTERSECT ".join(intersect_queries) + f" LIMIT {limit}"
        
        valid_group_ids = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(final_query, params)
            valid_group_ids = [row[0] for row in cursor.fetchall() if row[0] is not None]

        # Fetch the context for these valid groups
        return [self._get_row_context_by_group(gid) for gid in valid_group_ids]

    def _get_row_context_by_group(self, group_id: str) -> Dict:
        """Helper to assemble a row context dictionary from SQLite given a group_id"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT properties, row_index FROM nodes WHERE id = ?", (group_id,))
            group_data = cursor.fetchone()
            if not group_data: return {}
            
            group_props = json.loads(group_data[0])
            row_idx = group_data[1]
            
            cursor.execute("SELECT column, value FROM nodes WHERE group_id = ? AND labels LIKE '%Cell%' ORDER BY column", (group_id,))
            fields = [{"column": r[0], "value": r[1]} for r in cursor.fetchall()]
            selected_columns = group_props.get("selected_columns") or []
            column_order = {column: index for index, column in enumerate(selected_columns)}
            fields.sort(key=lambda field: column_order.get(field["column"], len(column_order)))
            
            return {
                "group_id": group_id,
                "primary_key_column": group_props.get("primary_key_column"),
                "primary_key_value": group_props.get("primary_key_value"),
                "row_index": row_idx,
                "row_fields": fields
            }

    def get_entity_context(self, entity_value: str, depth: int = 1, limit: int = 10000) -> List[Dict]:
        """Uses NetworkX to traverse the graph and retrieve localized context"""
        entity_value = str(entity_value).strip().lower()
        if not entity_value:
            return []

        # Find seed nodes directly from NetworkX
        seed_nodes = []
        allow_contains = len(entity_value) > 2
        for n, data in self.nx_graph.nodes(data=True):
            val = str(data.get('value', '')).lower()
            nid = str(n).lower()
            if val == entity_value or nid == entity_value or (allow_contains and (entity_value in val or entity_value in nid)):
                seed_nodes.append(n)
                if len(seed_nodes) >= limit: break

        contexts = []
        for seed in seed_nodes:
            seed_data = self.nx_graph.nodes[seed]
            group_id = seed_data.get('group_id')
            
            # Build ego graph for traversal context
            subgraph = nx.ego_graph(self.nx_graph, seed, radius=depth)
            nearby_values = []
            
            for nb in subgraph.nodes():
                if nb == seed: continue
                nb_data = self.nx_graph.nodes[nb]
                if 'Cell' in nb_data.get('labels', ''):
                    dist = nx.shortest_path_length(subgraph, source=seed, target=nb)
                    nearby_values.append({
                        "column": nb_data.get('column'),
                        "value": nb_data.get('value'),
                        "distance": dist
                    })
            
            # Fetch the core row data
            row_context = self._get_row_context_by_group(group_id)
            row_context["matched_column"] = seed_data.get('column')
            row_context["matched_value"] = seed_data.get('value')
            row_context["nearby_values"] = nearby_values[:25] # Limit nearby values
            
            contexts.append(row_context)
            
        return contexts

    def get_all_row_contexts(self, limit: int = 100000) -> List[Dict]:
        """Fetch all row groups for dataset-wide calculations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM nodes WHERE labels LIKE '%RowGroup%' ORDER BY row_index LIMIT ?", (limit,))
            group_ids = [r[0] for r in cursor.fetchall()]
            
        return [self._get_row_context_by_group(gid) for gid in group_ids]

    def generate_visualization(self, limit: int = 300) -> str:
        """
        Generate a high-fidelity interactive HTML visualization.
        Features directional arrows, edge labels, and distinct node styling.
        """
        from pyvis.network import Network
        
        # Initialize network: directed=True is REQUIRED for arrows
        net = Network(height='620px', width='100%', bgcolor='#ffffff', font_color='black', directed=True)
        
        # Extract a subgraph if the main graph is too large
        if len(self.nx_graph.nodes) > limit:
            print(f"[WARN] Graph too large for UI. Sampling {limit} nodes for visualization.")
            sampled_nodes = list(self.nx_graph.nodes)[:limit]
            subgraph = self.nx_graph.subgraph(sampled_nodes)
        else:
            subgraph = self.nx_graph
            
        # 1. Custom Node Styling
        for node_id, node_data in subgraph.nodes(data=True):
            labels = str(node_data.get('labels', ''))
            node_value = str(node_data.get('value', node_id))
            
            # Style based on entity type.
            if 'GraphColumn' in labels:
                color = '#6C63FF'  # Purple
                shape = 'box'
                size = 32
            elif 'RowGroup' in labels:
                color = '#FF7A59'  # Orange
                shape = 'hexagon'
                size = 30
            elif 'PrimaryEntity' in labels:
                color = '#00C49F'  # Teal
                shape = 'dot'
                size = 25
            else:
                color = '#0088FE'  # Blue
                shape = 'dot'
                size = 15
                
            # Add the node to PyVis
            net.add_node(
                node_id, 
                label=node_value, 
                title=f"ID: {node_id}\nType: {labels}", # Hover tooltip
                color=color, 
                shape=shape,
                size=size
            )

        # 2. Custom Edge Styling (Arrows and Text Labels)
        if subgraph.is_multigraph():
            edge_iterable = subgraph.edges(keys=True, data=True)
        else:
            edge_iterable = ((source, target, None, data) for source, target, data in subgraph.edges(data=True))

        for source, target, _, edge_data in edge_iterable:
            rel_type = edge_data.get('type', '')
            source_text = str(source)
            target_text = str(target)
            smooth_type = 'curvedCW' if source_text < target_text else 'curvedCCW'
            
            net.add_edge(
                source, 
                target, 
                label=rel_type,        # Text written on the line
                title=rel_type,        # Hover tooltip
                arrows='to',           # Arrowhead
                color='#888888',
                smooth={
                    "enabled": True,
                    "type": smooth_type,
                    "roundness": 0.28,
                },
            )

        # 3. Physics & Curvature Settings
        # We use a custom JavaScript options dictionary to force smooth, curved lines
        # This ensures bidirectional relationships (A -> B and B -> A) don't overlap.
        net.set_options("""
        var options = {
          "edges": {
            "font": {
              "size": 11,
              "align": "top",
              "background": "#ffffff"
            },
            "smooth": {
              "type": "curvedCW",
              "roundness": 0.28
            }
          },
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -120,
              "centralGravity": 0.01,
              "springLength": 200,
              "springConstant": 0.08
            },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based"
          }
        }
        """)
        
        return net.generate_html()
