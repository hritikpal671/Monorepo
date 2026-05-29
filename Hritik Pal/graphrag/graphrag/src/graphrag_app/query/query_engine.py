"""
Query Engine for GraphRAG - Main query processing and retrieval
"""

import json
import math
import re
import networkx as nx
import pandas as pd
from statistics import mean, median, multimode
from typing import Any, Dict, List, Optional, Tuple

from ..graph import GraphBuilder
from ..llm import OllamaLLMInterface


class GraphRAGQueryEngine:
    """Main query engine combining Graph search and LLM"""
    
    def __init__(self, graph_builder: GraphBuilder, llm_interface: OllamaLLMInterface):
        self.graph = graph_builder
        self.llm = llm_interface
        self.query_history = []
    
    def search_and_retrieve(self, query: str, top_k: int = 100000, max_context_rows: int = 100000) -> Dict[str, Any]:
        """Retrieve all row groups from the built graph scope for answer generation."""
        search_terms = self._fallback_search_terms(query)
        search_terms = list(dict.fromkeys(search_terms))
        
        retrieved_data = {
            "entities": [{"entity": term, "type": "query_term"} for term in search_terms],
            "search_results": [],
            "context": [],
            "retrieval_mode": "graph"
        }

        if search_terms:
            retrieved_data["search_results"] = self._get_matching_nodes_info(search_terms)

        retrieved_data["context"] = self.graph.get_all_row_contexts(limit=max_context_rows)
        retrieved_data["retrieval_mode"] = "full_graph"
        
        return retrieved_data

    def _traverse_graph_for_context(self, search_terms: List[str], depth: int = 10000, max_rows: int = 100000) -> List[Dict]:
        """Traverse the graph from matching nodes to retrieve context - TRUE GRAPH-BASED RETRIEVAL"""
        retrieved_rows = {}  # group_id -> (row_context, relevance_score)
        nx_graph = self.graph.nx_graph
        
        # Step 1: Find all seed nodes that match any search term
        seed_nodes = []
        for term in search_terms:
            term_lower = str(term).strip().lower()
            if not term_lower:
                continue
            
            # Find nodes matching this term in the graph
            for node_id, node_data in nx_graph.nodes(data=True):
                node_value = str(node_data.get('value', '')).lower()
                node_id_lower = str(node_id).lower()
                
                # Exact or contains match
                if node_value == term_lower or term_lower in node_value or node_id_lower == term_lower:
                    seed_nodes.append((node_id, node_data, 1.0))  # Relevance score = 1.0
        
        # Step 2: From each seed node, traverse the graph to find connected rows
        traversed_nodes = set()
        for seed_node_id, seed_data, seed_relevance in seed_nodes:
            group_id = seed_data.get('group_id')
            
            if not group_id:
                continue
            
            # Use ego_graph to find all connected nodes within distance=depth
            try:
                ego = nx.ego_graph(nx_graph, seed_node_id, radius=depth, undirected=True)
            except:
                ego = nx.Graph()
                ego.add_node(seed_node_id)
            
            # Collect all unique row groups from the ego graph
            for node in ego.nodes():
                node_data = nx_graph.nodes[node]
                node_group_id = node_data.get('group_id')
                
                if node_group_id and node_group_id not in traversed_nodes:
                    traversed_nodes.add(node_group_id)
                    
                    # Calculate relevance based on distance from seed
                    try:
                        distance = nx.shortest_path_length(ego, source=seed_node_id, target=node)
                    except:
                        distance = depth
                    
                    relevance = seed_relevance / (1.0 + distance)  # Closer nodes = higher relevance
                    
                    # Fetch the row context
                    row_context = self.graph._get_row_context_by_group(node_group_id)
                    if row_context:
                        if node_group_id not in retrieved_rows:
                            retrieved_rows[node_group_id] = (row_context, relevance)
                        else:
                            # Keep the highest relevance score for this row
                            old_context, old_score = retrieved_rows[node_group_id]
                            if relevance > old_score:
                                retrieved_rows[node_group_id] = (row_context, relevance)
        
        # Step 3: Sort by relevance and return
        sorted_rows = sorted(retrieved_rows.items(), key=lambda x: x[1][1], reverse=True)
        result = [row_context for _, (row_context, _) in sorted_rows[:max_rows]]
        
        return result

    def _get_matching_nodes_info(self, search_terms: List[str]) -> List[Dict]:
        """Get information about matching nodes in the graph"""
        matching_nodes = []
        nx_graph = self.graph.nx_graph
        
        for term in search_terms:
            term_lower = str(term).strip().lower()
            for node_id, node_data in nx_graph.nodes(data=True):
                node_value = str(node_data.get('value', '')).lower()
                if node_value == term_lower or term_lower in node_value:
                    matching_nodes.append({
                        "node_id": node_id,
                        "value": node_data.get('value'),
                        "labels": node_data.get('labels', ''),
                        "column": node_data.get('column'),
                        "group_id": node_data.get('group_id')
                    })
        
        return matching_nodes

    def _requires_full_dataset(self, query: str) -> bool:
        normalized = query.lower()
        full_dataset_patterns = [
            r"\ball\b", r"\bevery\b", r"\beach\b", r"\bentire\b", r"\bwhole\b",
            r"\bdataset\b", r"\btable\b", r"\btotal\b", r"\bcount\b", r"\baverage\b",
            r"\bmean\b", r"\bsum\b", r"\bminimum\b", r"\bmaximum\b", r"\bmin\b", r"\bmax\b",
            r"\bhighest\b", r"\blowest\b", r"\btop\b", r"\bbottom\b", r"\blist\b",
            r"\bcompare\b", r"\boverall\b", r"\bsummary\b", r"\btrend\b", r"\bpattern\b",
        ]
        return any(re.search(pattern, normalized) for pattern in full_dataset_patterns)

    def _deduplicate_context(self, context_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduplicated = []
        seen_group_ids = set()
        for item in context_items:
            row_context = item.get("row_context", item)
            group_id = row_context.get("group_id")
            if group_id and group_id in seen_group_ids:
                continue
            if group_id:
                seen_group_ids.add(group_id)
            deduplicated.append(item)
        return deduplicated

    def _normalize_entities(self, entities: Any) -> List[Dict[str, str]]:
        if isinstance(entities, dict): entities = [entities]
        elif not isinstance(entities, list): entities = []
        normalized = []
        for entity_info in entities:
            if isinstance(entity_info, dict) and entity_info.get("entity"):
                normalized.append({
                    "entity": str(entity_info.get("entity")),
                    "type": str(entity_info.get("type", "unknown"))
                })
            elif isinstance(entity_info, str) and entity_info.strip():
                normalized.append({"entity": entity_info.strip(), "type": "unknown"})
        return normalized

    def _fallback_search_terms(self, query: str) -> List[str]:
        stop_words = {"what", "when", "where", "which", "who", "whose", "tell", "show",
                      "about", "from", "that", "this", "with", "the", "and", "for",
                      "row", "data", "dataset", "column", "columns", "value", "values"}
        terms = []
        for row_term in re.findall(r"\brow\s+([A-Za-z0-9_.@/-]+)", query, flags=re.IGNORECASE):
            if row_term.lower() not in stop_words:
                terms.append(row_term)

        for term in re.findall(r"[A-Za-z0-9_.@/-]+", query):
            normalized = term.lower()
            if normalized in stop_words or term in terms: continue
            if len(term) > 2 or term.isupper() or term.isdigit():
                terms.append(term)
        return terms
    
    def format_context_for_llm(self, context: Dict[str, Any]) -> str:
        formatted = "Retrieved Context from Knowledge Graph:\n"
        formatted += "=" * 50 + "\n\n"
        
        if context.get("entities"):
            formatted += "Entities Mentioned:\n"
            for entity in context["entities"]:
                formatted += f"  - {entity.get('entity')} ({entity.get('type', 'unknown')})\n"
            formatted += "\n"
        
        if context.get("search_results"):
            formatted += "Search Results:\n"
            for result in context["search_results"]:
                formatted += f"  - {json.dumps(result, indent=2)}\n"
            formatted += "\n"

        if context.get("context"):
            retrieval_mode = context.get("retrieval_mode", "entity")
            formatted += f"Matched Row Context ({retrieval_mode}):\n"
            formatted += f"Total row groups supplied: {len(context['context'])}\n"
            for item in context["context"]:
                row_context = item.get("row_context", item)
                row_fields = row_context.get("row_fields", [])
                field_text = " | ".join(
                    f"{field.get('column')}={field.get('value')}"
                    for field in row_fields
                )
                formatted += (
                    f"  - row_index={row_context.get('row_index')} "
                    f"group_id={row_context.get('group_id')} "
                    f"primary_key={row_context.get('primary_key_column')}:{row_context.get('primary_key_value')} "
                    f"fields: {field_text}\n"
                )
            formatted += "\n"
        
        return formatted

    def _rows_as_records(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        records = []
        for row in rows:
            record = {
                "__row_index": row.get("row_index"),
                "__group_id": row.get("group_id"),
                "__primary_key_column": row.get("primary_key_column"),
                "__primary_key_value": row.get("primary_key_value"),
            }
            for field in row.get("row_fields", []):
                record[str(field.get("column"))] = field.get("value")
            records.append(record)
        return records

    def _column_names(self, records: List[Dict[str, Any]]) -> List[str]:
        columns = []
        for record in records:
            for column in record:
                if column.startswith("__") or column in columns:
                    continue
                columns.append(column)
        return columns

    def _match_column(self, query: str, columns: List[str]) -> Optional[str]:
        normalized_query = self._normalize_text(query)
        exact_matches = [
            column for column in columns
            if re.search(rf"\b{re.escape(self._normalize_text(column))}\b", normalized_query)
        ]
        if exact_matches:
            return max(exact_matches, key=len)

        for column in columns:
            column_parts = [part for part in re.split(r"[^a-z0-9]+", self._normalize_text(column)) if part]
            if column_parts and all(part in normalized_query for part in column_parts):
                return column
        return None

    def _mentioned_columns(self, query: str, columns: List[str]) -> List[str]:
        normalized_query = self._normalize_text(query)
        matches = []
        for column in columns:
            normalized_column = self._normalize_text(column)
            column_parts = [part for part in re.split(r"[^a-z0-9]+", normalized_column) if part]
            if normalized_column and re.search(rf"\b{re.escape(normalized_column)}\b", normalized_query):
                matches.append(column)
            elif column_parts and all(part in normalized_query for part in column_parts):
                matches.append(column)
        return list(dict.fromkeys(matches))

    def _normalize_text(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value).strip().lower())

    def _to_number(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip().replace(",", "")
        text = re.sub(r"[%$]", "", text)
        try:
            return float(text)
        except ValueError:
            return None

    def _find_filters(self, query: str, records: List[Dict[str, Any]], columns: List[str]) -> List[Tuple[str, str]]:
        normalized_query = self._normalize_text(query)
        filters = []

        for column in columns:
            normalized_column = self._normalize_text(column)
            for record in records:
                value = record.get(column)
                if value is None or str(value).strip() == "":
                    continue

                normalized_value = self._normalize_text(value)
                if len(normalized_value) < 2:
                    continue

                column_value_patterns = [
                    rf"\b{re.escape(normalized_column)}\b\s*(?:=|is|as|of|for|:)\s*{re.escape(normalized_value)}\b",
                    rf"\b{re.escape(normalized_value)}\b\s*(?:in|under|from|for)\s*\b{re.escape(normalized_column)}\b",
                ]
                if any(re.search(pattern, normalized_query) for pattern in column_value_patterns):
                    filters.append((column, str(value)))
                elif len(normalized_value) > 2 and re.search(rf"\b{re.escape(normalized_value)}\b", normalized_query):
                    filters.append((column, str(value)))

        deduped = []
        seen = set()
        for item in filters:
            key = (item[0], self._normalize_text(item[1]))
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    def _apply_filters(self, records: List[Dict[str, Any]], filters: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        if not filters:
            return records

        filtered = []
        for record in records:
            matched = True
            for column, expected_value in filters:
                actual_value = self._normalize_text(record.get(column, ""))
                expected_text = self._normalize_text(expected_value)
                if actual_value != expected_text and expected_text not in actual_value:
                    matched = False
                    break
            if matched:
                filtered.append(record)
        return filtered

    def _format_records(self, records: List[Dict[str, Any]], columns: List[str]) -> str:
        if not records:
            return "No matching rows were found in the graph."

        lines = []
        for record in records:
            parts = [f"{column}: {record.get(column, '')}" for column in columns if column in record]
            lines.append(f"- Row {record.get('__row_index')}: " + "; ".join(parts))
        return "\n".join(lines)

    def _format_number(self, value: Any) -> str:
        if value is None:
            return "N/A"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if math.isnan(number) or math.isinf(number):
            return "N/A"
        return f"{number:g}"

    def _numeric_columns(self, records: List[Dict[str, Any]], columns: List[str]) -> List[str]:
        return [
            column for column in columns
            if any(self._to_number(record.get(column)) is not None for record in records)
        ]

    def _numeric_values(self, records: List[Dict[str, Any]], column: str) -> List[Tuple[Dict[str, Any], float]]:
        values = []
        for record in records:
            number = self._to_number(record.get(column))
            if number is not None:
                values.append((record, number))
        return values

    def _column_position(self, query: str, column: str) -> int:
        normalized_query = self._normalize_text(query)
        normalized_column = self._normalize_text(column)
        candidates = [normalized_column]
        if normalized_column.endswith("y"):
            candidates.append(f"{normalized_column[:-1]}ies")
        candidates.append(f"{normalized_column}s")

        positions = [
            normalized_query.find(candidate)
            for candidate in candidates
            if candidate and normalized_query.find(candidate) >= 0
        ]
        return min(positions) if positions else 10**9

    def _mentioned_columns_ordered(self, query: str, columns: List[str]) -> List[str]:
        mentioned = self._mentioned_columns(query, columns)
        return sorted(mentioned, key=lambda column: (self._column_position(query, column), columns.index(column)))

    def _looks_like_measure_column(self, column: str) -> bool:
        normalized = self._normalize_text(column)
        weak_measure_names = {"id", "key", "code", "year", "month", "quarter", "date", "time", "period"}
        return not any(part in weak_measure_names for part in re.split(r"[^a-z0-9]+", normalized) if part)

    def _select_metric_column(
        self,
        question: str,
        records: List[Dict[str, Any]],
        columns: List[str],
        mentioned_columns: List[str],
    ) -> Optional[str]:
        numeric_columns = self._numeric_columns(records, columns)
        if not numeric_columns:
            return None

        mentioned_numeric = [column for column in mentioned_columns if column in numeric_columns]
        if mentioned_numeric:
            preferred = [column for column in mentioned_numeric if self._looks_like_measure_column(column)]
            return preferred[0] if preferred else mentioned_numeric[0]

        target_column = self._match_column(question, columns)
        if target_column in numeric_columns:
            return target_column

        preferred = [column for column in numeric_columns if self._looks_like_measure_column(column)]
        return preferred[0] if preferred else numeric_columns[0]

    def _select_group_columns(
        self,
        question: str,
        columns: List[str],
        mentioned_columns: List[str],
        metric_column: Optional[str],
    ) -> List[str]:
        group_columns = [column for column in mentioned_columns if column != metric_column]
        if group_columns:
            return group_columns[:2]

        normalized_question = self._normalize_text(question)
        for column in columns:
            normalized_column = self._normalize_text(column)
            if re.search(rf"\b(by|per|each|every|for each)\s+{re.escape(normalized_column)}s?\b", normalized_question):
                return [column]

        return []

    def _default_label_columns(
        self,
        columns: List[str],
        records: List[Dict[str, Any]],
        metric_column: Optional[str] = None,
    ) -> List[str]:
        numeric_columns = set(self._numeric_columns(records, columns))
        labels = [column for column in columns if column != metric_column and column not in numeric_columns]
        if labels:
            return labels[:2]
        return [column for column in columns if column != metric_column][:2]

    def _extract_n(self, question: str, default: int = 5) -> int:
        normalized_question = self._normalize_text(question)
        match = re.search(r"\b(?:top|bottom|first|last)\s+(\d+)\b", normalized_question)
        if not match:
            match = re.search(r"\bnext\s+(\d+)\b", normalized_question)
        if not match:
            match = re.search(r"\b(\d+)\s+(?:highest|lowest|largest|smallest|best|worst)\b", normalized_question)
        if not match:
            return default
        return max(1, min(int(match.group(1)), 100))

    def _detect_operation(self, question: str) -> Optional[str]:
        normalized = self._normalize_text(question)
        operation_patterns = [
            ("forecast", r"\b(forecast|predict|projection|project|future|next)\b"),
            ("trend", r"\b(trend|trending|growth|decline|increase|decrease|over time|pattern)\b"),
            ("regression", r"\b(regression|linear fit|line of best fit|slope|intercept|r squared|r2)\b"),
            ("correlation", r"\b(correlation|correlate|relationship between|association between)\b"),
            ("quartiles", r"\b(quartile|quartiles|q1|q2|q3|iqr)\b"),
            ("percentile", r"\b(percentile|percentiles|p\d{1,2})\b"),
            ("running_total", r"\b(running total|cumulative|cumsum|cumulative sum)\b"),
            ("standard_deviation", r"\b(standard deviation|std dev|stdev|std)\b"),
            ("variance", r"\b(variance|var)\b"),
            ("percentage", r"\b(percentage|percent|share|contribution)\b"),
            ("difference", r"\b(difference|delta|gap|change between|minus)\b"),
            ("ratio", r"\b(ratio|proportion|divided by|per)\b"),
            ("product", r"\b(product of|multiply|multiplied|multiplication)\b"),
            ("median", r"\b(median)\b"),
            ("mode", r"\b(mode|most common|frequent|frequency)\b"),
            ("average", r"\b(avg|average|mean)\b"),
            ("sum", r"\b(sum|total)\b"),
            ("count", r"\b(count|how many|number of)\b"),
            ("max", r"\b(max|maximum|highest|largest|biggest|best|top|most)\b"),
            ("min", r"\b(min|minimum|lowest|smallest|least|worst|bottom|fewest)\b"),
            ("range", r"\b(range|spread)\b"),
            ("list", r"\b(list|show|display)\b"),
        ]
        for operation, pattern in operation_patterns:
            if re.search(pattern, normalized):
                return operation
        return None

    def _aggregate_values(self, values: List[float], operation: str) -> Optional[float]:
        if not values:
            return None
        if operation in {"sum", "max", "min", "range", "count"}:
            if operation == "sum":
                return sum(values)
            if operation == "max":
                return max(values)
            if operation == "min":
                return min(values)
            if operation == "range":
                return max(values) - min(values)
            return float(len(values))
        if operation == "average":
            return mean(values)
        if operation == "median":
            return median(values)
        if operation == "product":
            product = 1.0
            for value in values:
                product *= value
            return product
        if operation == "variance":
            return pd.Series(values, dtype="float64").var(ddof=1) if len(values) > 1 else 0.0
        if operation == "standard_deviation":
            return pd.Series(values, dtype="float64").std(ddof=1) if len(values) > 1 else 0.0
        return None

    def _operation_label(self, operation: str) -> str:
        labels = {
            "sum": "total",
            "average": "average",
            "median": "median",
            "mode": "mode",
            "count": "count",
            "min": "lowest",
            "max": "highest",
            "range": "range",
            "product": "product",
            "variance": "variance",
            "standard_deviation": "standard deviation",
        }
        return labels.get(operation, operation.replace("_", " "))

    def _row_label(self, record: Dict[str, Any], label_columns: List[str]) -> str:
        labels = [
            f"{column}: {record.get(column)}"
            for column in label_columns
            if column in record and str(record.get(column, "")).strip()
        ]
        return ", ".join(labels) if labels else f"row {record.get('__row_index')}"

    def _format_grouped_result(
        self,
        grouped: pd.Series,
        group_columns: List[str],
        metric_column: Optional[str],
        operation: str,
        limit: int = 20,
    ) -> str:
        if grouped.empty:
            return "No matching values were found for that grouped calculation."

        title_metric = metric_column or "rows"
        lines = [
            f"{self._operation_label(operation).title()} by {', '.join(group_columns)} for {title_metric}:"
        ]
        for key, value in grouped.head(limit).items():
            if not isinstance(key, tuple):
                key = (key,)
            label = ", ".join(f"{column}: {part}" for column, part in zip(group_columns, key))
            lines.append(f"- {label} -> {self._format_number(value)}")
        return "\n".join(lines)

    def _time_column(self, records: List[Dict[str, Any]], columns: List[str]) -> Optional[str]:
        name_candidates = [
            column for column in columns
            if re.search(r"\b(date|time|year|month|quarter|period)\b", self._normalize_text(column))
        ]
        candidates = name_candidates + [column for column in columns if column not in name_candidates]
        for column in candidates:
            values = [record.get(column) for record in records if record.get(column) not in (None, "")]
            if not values:
                continue
            parsed = pd.to_datetime(pd.Series(values), errors="coerce")
            numeric_values = [self._to_number(value) for value in values]
            numeric_count = sum(value is not None for value in numeric_values)
            if parsed.notna().sum() >= max(2, len(values) // 2) or numeric_count >= max(2, len(values) // 2):
                return column
        return None

    def _analytics_frame(self, records: List[Dict[str, Any]], columns: List[str]) -> pd.DataFrame:
        frame = pd.DataFrame([{column: record.get(column) for column in columns} for record in records])
        return frame

    def _deterministic_graph_answer(self, question: str, context: Dict[str, Any]) -> Optional[str]:
        rows = context.get("context") or []
        records = self._rows_as_records(rows)
        if not records:
            return "The graph does not contain any row groups to answer from."

        columns = self._column_names(records)
        if not columns:
            return "The graph does not contain any selected columns to answer from."

        normalized_question = self._normalize_text(question)
        filters = self._find_filters(question, records, columns)
        filtered_records = self._apply_filters(records, filters)
        if not filtered_records:
            return "No graph rows match the requested filters."

        mentioned_columns = self._mentioned_columns_ordered(question, columns)
        operation = self._detect_operation(question)
        metric_column = self._select_metric_column(question, filtered_records, columns, mentioned_columns)
        group_columns = self._select_group_columns(question, columns, mentioned_columns, metric_column)
        filter_columns = {column for column, _ in filters}
        if filters and group_columns and all(column in filter_columns for column in group_columns):
            group_columns = []
        numeric_columns = self._numeric_columns(filtered_records, columns)
        mentioned_numeric_columns = [column for column in mentioned_columns if column in numeric_columns]
        if operation in {"max", "min"} and not mentioned_numeric_columns and re.search(r"\b(most|fewest)\b", normalized_question):
            metric_column = None
            group_columns = mentioned_columns[:1]

        if operation == "count":
            if group_columns:
                frame = self._analytics_frame(filtered_records, columns)
                grouped = frame.groupby(group_columns, dropna=False).size().sort_values(ascending=False)
                return self._format_grouped_result(grouped, group_columns, None, "count")
            return f"{len(filtered_records)} row(s) match in the graph."

        if operation == "mode":
            mode_column = next((column for column in mentioned_columns if column != metric_column), None) or metric_column
            if not mode_column:
                return None
            values = [
                str(record.get(mode_column))
                for record in filtered_records
                if record.get(mode_column) not in (None, "")
            ]
            if not values:
                return f"No values were found for {mode_column}."
            modes = multimode(values)
            count = values.count(modes[0]) if modes else 0
            return f"The mode of {mode_column} is {', '.join(modes[:10])} ({count} occurrence(s))."

        if operation == "percentage":
            if not metric_column:
                if group_columns:
                    frame = self._analytics_frame(filtered_records, columns)
                    counts = frame.groupby(group_columns, dropna=False).size()
                    percentages = (counts / counts.sum() * 100).sort_values(ascending=False)
                    return self._format_grouped_result(percentages, group_columns, None, "percentage")
                percent = len(filtered_records) / len(records) * 100 if records else 0
                return f"Matching rows are {self._format_number(percent)}% of all graph rows."

            filtered_values = [value for _, value in self._numeric_values(filtered_records, metric_column)]
            all_values = [value for _, value in self._numeric_values(records, metric_column)]
            if group_columns:
                frame = self._analytics_frame(filtered_records, columns)
                frame["__metric"] = frame[metric_column].map(self._to_number)
                grouped = frame.dropna(subset=["__metric"]).groupby(group_columns, dropna=False)["__metric"].sum()
                percentages = (grouped / grouped.sum() * 100).sort_values(ascending=False)
                return self._format_grouped_result(percentages, group_columns, metric_column, "percentage")
            if not all_values:
                return f"No numeric values were found for {metric_column}."
            percent = (sum(filtered_values) / sum(all_values) * 100) if sum(all_values) else 0
            return f"The selected {metric_column} total is {self._format_number(percent)}% of the overall {metric_column} total."

        if operation == "correlation":
            selected_numeric = [column for column in mentioned_columns if column in numeric_columns]
            if len(selected_numeric) < 2:
                selected_numeric = numeric_columns[:2]
            if len(selected_numeric) < 2:
                return "At least two numeric columns are needed for correlation."
            left, right = selected_numeric[:2]
            frame = self._analytics_frame(filtered_records, columns)
            series_left = frame[left].map(self._to_number)
            series_right = frame[right].map(self._to_number)
            corr = series_left.corr(series_right)
            return f"The Pearson correlation between {left} and {right} is {self._format_number(corr)} across {len(filtered_records)} row(s)."

        if operation == "regression":
            selected_numeric = [column for column in mentioned_columns if column in numeric_columns]
            if len(selected_numeric) < 2:
                selected_numeric = numeric_columns[:2]
            if len(selected_numeric) < 2:
                return "At least two numeric columns are needed for regression analysis."
            y_column, x_column = selected_numeric[:2]
            frame = self._analytics_frame(filtered_records, columns)
            x = frame[x_column].map(self._to_number)
            y = frame[y_column].map(self._to_number)
            pair_frame = pd.DataFrame({"x": x, "y": y}).dropna()
            if len(pair_frame) < 2:
                return "At least two complete numeric rows are needed for regression analysis."
            slope, intercept = pd.Series(pair_frame["x"]).cov(pair_frame["y"]) / pd.Series(pair_frame["x"]).var(), 0.0
            intercept = pair_frame["y"].mean() - slope * pair_frame["x"].mean()
            predictions = intercept + slope * pair_frame["x"]
            ss_res = ((pair_frame["y"] - predictions) ** 2).sum()
            ss_tot = ((pair_frame["y"] - pair_frame["y"].mean()) ** 2).sum()
            r_squared = 1 - (ss_res / ss_tot) if ss_tot else 1.0
            return (
                f"Linear regression for {y_column} using {x_column}: "
                f"{y_column} = {self._format_number(intercept)} + {self._format_number(slope)} * {x_column}. "
                f"R^2 = {self._format_number(r_squared)} across {len(pair_frame)} row(s)."
            )

        if operation in {"trend", "forecast"}:
            if not metric_column:
                return "A numeric metric column is needed for trend or forecasting analysis."
            time_column = self._time_column(filtered_records, columns)
            if not time_column:
                return "A date, time, year, month, quarter, or ordered numeric column is needed for trend analysis."
            frame = self._analytics_frame(filtered_records, columns)
            frame["__metric"] = frame[metric_column].map(self._to_number)
            frame["__time"] = pd.to_datetime(frame[time_column], errors="coerce")
            numeric_time = frame[time_column].map(self._to_number)
            if frame["__time"].notna().sum() < 2 and numeric_time.notna().sum() >= 2:
                frame["__time_sort"] = numeric_time
                time_labels = frame[time_column]
            else:
                frame["__time_sort"] = frame["__time"]
                time_labels = frame[time_column]
            trend_frame = frame.dropna(subset=["__metric", "__time_sort"]).copy()
            if trend_frame.empty:
                return f"No usable {metric_column} and {time_column} pairs were found."
            grouped = trend_frame.groupby("__time_sort", dropna=False)["__metric"].sum().sort_index()
            if len(grouped) < 2:
                return "At least two time points are needed for trend or forecasting analysis."
            first_value = grouped.iloc[0]
            last_value = grouped.iloc[-1]
            change = last_value - first_value
            percent_change = (change / first_value * 100) if first_value else 0
            direction = "increased" if change > 0 else "decreased" if change < 0 else "stayed flat"

            if operation == "forecast":
                periods = self._extract_n(question, default=3)
                x = pd.Series(range(len(grouped)), dtype="float64")
                y = pd.Series(grouped.values, dtype="float64")
                slope = x.cov(y) / x.var() if x.var() else 0.0
                intercept = y.mean() - slope * x.mean()
                lines = [f"Simple linear forecast for {metric_column} based on {time_column}:"]
                for step in range(1, periods + 1):
                    forecast_value = intercept + slope * (len(grouped) - 1 + step)
                    lines.append(f"- Period +{step}: {self._format_number(forecast_value)}")
                lines.append(
                    f"Historical trend {direction} by {self._format_number(change)} "
                    f"({self._format_number(percent_change)}%)."
                )
                return "\n".join(lines)

            return (
                f"{metric_column} {direction} from {self._format_number(first_value)} to "
                f"{self._format_number(last_value)}, a change of {self._format_number(change)} "
                f"({self._format_number(percent_change)}%) across {len(grouped)} {time_column} point(s)."
            )

        if operation in {"difference", "ratio"}:
            selected_numeric = [column for column in mentioned_columns if column in numeric_columns]
            if len(selected_numeric) < 2:
                selected_numeric = numeric_columns[:2]
            if len(selected_numeric) < 2:
                return "At least two numeric columns are needed for difference or ratio calculations."
            left, right = selected_numeric[:2]
            left_total = sum(value for _, value in self._numeric_values(filtered_records, left))
            right_total = sum(value for _, value in self._numeric_values(filtered_records, right))
            if operation == "difference":
                return f"The difference between total {left} and total {right} is {self._format_number(left_total - right_total)}."
            if right_total == 0:
                return f"The ratio of {left} to {right} cannot be computed because total {right} is zero."
            return f"The ratio of total {left} to total {right} is {self._format_number(left_total / right_total)}."

        if operation in {"max", "min"} and not metric_column and group_columns:
            frame = self._analytics_frame(filtered_records, columns)
            count_group = [group_columns[0]]
            grouped = frame.groupby(count_group, dropna=False).size().sort_values(ascending=(operation == "min"))
            n = self._extract_n(question, default=5)
            return self._format_grouped_result(grouped, count_group, None, "count", limit=n)

        if operation == "running_total":
            if not metric_column:
                return "A numeric metric column is needed for a running total."
            values = self._numeric_values(filtered_records, metric_column)
            if not values:
                return f"No numeric values were found for {metric_column}."
            time_column = self._time_column(filtered_records, columns)
            ordered_records = filtered_records
            if time_column:
                ordered_records = sorted(
                    filtered_records,
                    key=lambda record: (
                        pd.to_datetime(record.get(time_column), errors="coerce"),
                        self._to_number(record.get(time_column)) or 0,
                    ),
                )
            label_columns = self._default_label_columns(columns, filtered_records, metric_column)
            running = 0.0
            lines = [f"Running total for {metric_column}:"]
            for record in ordered_records[:25]:
                value = self._to_number(record.get(metric_column))
                if value is None:
                    continue
                running += value
                lines.append(f"- {self._row_label(record, label_columns)} -> {self._format_number(running)}")
            return "\n".join(lines)

        if operation in {"quartiles", "percentile"}:
            if not metric_column:
                return "A numeric metric column is needed for quartiles or percentiles."
            values = [value for _, value in self._numeric_values(filtered_records, metric_column)]
            if not values:
                return f"No numeric values were found for {metric_column}."
            series = pd.Series(values, dtype="float64")
            if operation == "quartiles":
                q1, q2, q3 = series.quantile([0.25, 0.5, 0.75]).tolist()
                return (
                    f"Quartiles for {metric_column}: "
                    f"Q1={self._format_number(q1)}, Q2/median={self._format_number(q2)}, Q3={self._format_number(q3)}."
                )
            match = re.search(r"\b(?:p|percentile\s*)(\d{1,2})\b", normalized_question)
            if not match:
                match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+percentile\b", normalized_question)
            percentile = int(match.group(1)) if match else 90
            percentile = max(0, min(percentile, 100))
            value = series.quantile(percentile / 100)
            return f"The {percentile}th percentile of {metric_column} is {self._format_number(value)}."

        if metric_column and operation in {"sum", "average", "median", "max", "min", "range", "product", "variance", "standard_deviation"}:
            values = self._numeric_values(filtered_records, metric_column)
            if not values:
                return f"No numeric values were found for {metric_column}."

            if group_columns:
                frame = self._analytics_frame(filtered_records, columns)
                frame["__metric"] = frame[metric_column].map(self._to_number)
                metric_frame = frame.dropna(subset=["__metric"])
                grouped_obj = metric_frame.groupby(group_columns, dropna=False)["__metric"]
                if operation == "sum":
                    grouped = grouped_obj.sum().sort_values(ascending=False)
                elif operation == "average":
                    grouped = grouped_obj.mean().sort_values(ascending=False)
                elif operation == "median":
                    grouped = grouped_obj.median().sort_values(ascending=False)
                elif operation == "max":
                    grouped = grouped_obj.sum().sort_values(ascending=False)
                elif operation == "min":
                    grouped = grouped_obj.sum().sort_values(ascending=True)
                elif operation == "range":
                    grouped = (grouped_obj.max() - grouped_obj.min()).sort_values(ascending=False)
                elif operation == "product":
                    grouped = grouped_obj.prod().sort_values(ascending=False)
                elif operation == "variance":
                    grouped = grouped_obj.var().fillna(0).sort_values(ascending=False)
                else:
                    grouped = grouped_obj.std().fillna(0).sort_values(ascending=False)

                if operation in {"max", "min"}:
                    default_limit = 5 if re.search(r"\b(top|bottom)\b", normalized_question) else 1
                else:
                    default_limit = 20
                n = self._extract_n(question, default=default_limit)
                return self._format_grouped_result(grouped, group_columns, metric_column, operation, limit=n)

            numeric_values = [value for _, value in values]
            if operation in {"max", "min"}:
                reverse = operation == "max"
                n = self._extract_n(question, default=1)
                ranked = sorted(values, key=lambda item: item[1], reverse=reverse)[:n]
                label_columns = self._default_label_columns(columns, filtered_records, metric_column)
                lines = [f"{self._operation_label(operation).title()} {metric_column} value(s):"]
                for record, value in ranked:
                    lines.append(f"- {self._row_label(record, label_columns)} -> {self._format_number(value)}")
                if n == 1:
                    lines.append(self._format_records([ranked[0][0]], columns))
                return "\n".join(lines)

            aggregate = self._aggregate_values(numeric_values, operation)
            if aggregate is None:
                return None
            return (
                f"The {self._operation_label(operation)} of {metric_column} is "
                f"{self._format_number(aggregate)} across {len(numeric_values)} graph row(s)."
            )

        if re.search(r"\b(list|show|display)\b", normalized_question):
            return self._format_records(filtered_records, columns)

        if re.search(r"\b(give|which|what|who|where)\b", normalized_question):
            output_columns = mentioned_columns if mentioned_columns and filters else columns
            if metric_column and metric_column not in output_columns:
                output_columns.append(metric_column)
            return self._format_records(filtered_records, output_columns)

        if filters:
            return self._format_records(filtered_records, mentioned_columns or columns)

        return None
    
    def answer_question(self, question: str, use_graph_context: bool = True) -> Dict[str, Any]:
        result = {
            "question": question, "answer": "", "confidence": 0.0,
            "sources": [], "reasoning": ""
        }
        
        try:
            if use_graph_context:
                context = self.search_and_retrieve(question)
                formatted_context = self.format_context_for_llm(context)
                result["sources"] = context.get("search_results", [])
                result["retrieved_row_groups"] = len(context.get("context", []))
                result["retrieval_mode"] = context.get("retrieval_mode", "entity")
            else:
                context = {}
                formatted_context = ""

            deterministic_answer = self._deterministic_graph_answer(question, context) if use_graph_context else None
            if deterministic_answer:
                result["answer"] = deterministic_answer
                result["confidence"] = 0.95
                result["reasoning"] = f"Computed deterministically from {result.get('retrieved_row_groups', 0)} graph row groups"
                result["retrieval_mode"] = f"{result.get('retrieval_mode', 'graph')}_deterministic"
                self.query_history.append(result)
                return result
            
            answer = self.llm.generate_query_response(question, formatted_context)
            result["answer"] = answer
            result["confidence"] = 0.85 
            result["reasoning"] = f"Generated from {result.get('retrieved_row_groups', 0)} retrieved row groups"
            
        except Exception as e:
            result["answer"] = f"Error processing question: {str(e)}"
            result["confidence"] = 0.0
        
        self.query_history.append(result)
        return result
    
    def batch_answer_questions(self, questions: List[str]) -> List[Dict[str, Any]]:
        results = []
        for question in questions:
            result = self.answer_question(question)
            results.append(result)
            print(f"[OK] Answered: {question[:50]}...")
        return results
    
    def get_graph_summary(self) -> str:
        stats = self.graph.get_graph_stats()
        summary_text = f"""
Knowledge Graph Summary:
- Total Nodes: {stats.get('total_nodes', 0)}
- Total Relationships: {stats.get('total_relationships', 0)}
- Node Types: {len(stats.get('node_labels', []))}
"""
        insights = self.llm.generate_graph_insights(summary_text)
        return f"{summary_text}\n\nGenerated Insights:\n{insights}"
    
    def explore_relationships(self, entity: str, depth: int = 2) -> Dict[str, Any]:
        context = self.graph.get_entity_context(entity, depth=depth)
        return {
            "entity": entity,
            "depth": depth,
            "relationships": context,
            "count": len(context)
        }
    
    def get_query_history(self) -> List[Dict[str, Any]]:
        return self.query_history
    
    def clear_history(self):
        self.query_history = []
