"""
Neo4j graph store service for Graph RAG.
"""

import logging
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings

logger = logging.getLogger("serpent.graph_store")


class GraphNode:
    """Represents an entity node in the knowledge graph."""

    def __init__(self, id: str, name: str, type: str, properties: dict) -> None:
        self.id = id
        self.name = name
        self.type = type
        self.properties = properties


class GraphEdge:
    """Represents a relationship edge."""

    def __init__(
        self, source: str, target: str, type: str, properties: dict
    ) -> None:
        self.source = source
        self.target = target
        self.type = type
        self.properties = properties


class Neo4jService:
    """Manages Neo4j knowledge graph operations."""

    def __init__(self) -> None:
        self._driver: Optional[AsyncDriver] = None

    async def initialize(self) -> None:
        """Connect to Neo4j."""
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("Neo4j service initialized", extra={"uri": settings.neo4j_uri})

    async def close(self) -> None:
        """Close Neo4j driver."""
        if self._driver:
            await self._driver.close()

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        properties: Optional[dict] = None,
        collection: str = "default",
    ) -> str:
        """Create or merge an entity node. Returns node element ID."""
        props = properties or {}
        async with self._driver.session() as session:
            result = await session.run(
                """
                MERGE (e:Entity {name: $name, type: $type, collection: $collection})
                ON CREATE SET e += $props, e.created_at = datetime()
                ON MATCH SET e += $props, e.updated_at = datetime()
                RETURN elementId(e) as id
                """,
                name=name,
                type=entity_type,
                collection=collection,
                props=props,
            )
            record = await result.single()
            return record["id"]

    async def create_relationship(
        self,
        source_name: str,
        target_name: str,
        rel_type: str,
        properties: Optional[dict] = None,
        collection: str = "default",
    ) -> None:
        """Create a relationship between two entities."""
        props = properties or {}
        async with self._driver.session() as session:
            await session.run(
                f"""
                MATCH (a:Entity {{name: $source, collection: $collection}})
                MATCH (b:Entity {{name: $target, collection: $collection}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """,
                source=source_name,
                target=target_name,
                collection=collection,
                props=props,
            )

    async def bulk_create_entities(
        self,
        entities: list[dict],
        collection: str = "default",
    ) -> int:
        """Batch create/merge entities. Each dict: {name, type, properties?}.

        Returns count of processed entities.
        """
        if not entities:
            return 0
        params = [
            {
                "name": e["name"],
                "type": e["type"],
                "props": e.get("properties", {}),
            }
            for e in entities
        ]
        async with self._driver.session() as session:
            result = await session.run(
                """
                UNWIND $entities AS entity
                MERGE (e:Entity {name: entity.name, type: entity.type, collection: $collection})
                ON CREATE SET e += entity.props, e.created_at = datetime()
                ON MATCH SET e += entity.props, e.updated_at = datetime()
                RETURN count(e) as cnt
                """,
                entities=params,
                collection=collection,
            )
            record = await result.single()
            return record["cnt"] if record else 0

    async def bulk_create_relationships(
        self,
        relationships: list[dict],
        collection: str = "default",
    ) -> int:
        """Batch create relationships. Each dict: {source, target, type, properties?}.

        Returns count of processed relationships.
        """
        if not relationships:
            return 0
        params = [
            {
                "source": r["source"],
                "target": r["target"],
                "rel_type": r["type"],
                "props": r.get("properties", {}),
            }
            for r in relationships
        ]
        # Neo4j doesn't allow parameterized rel types in MERGE directly,
        # so we use APOC for dynamic relationship creation
        async with self._driver.session() as session:
            result = await session.run(
                """
                UNWIND $rels AS rel
                MATCH (a:Entity {name: rel.source, collection: $collection})
                MATCH (b:Entity {name: rel.target, collection: $collection})
                CALL apoc.merge.relationship(a, rel.rel_type, {}, rel.props, b, {})
                YIELD rel AS r
                RETURN count(r) as cnt
                """,
                rels=params,
                collection=collection,
            )
            record = await result.single()
            return record["cnt"] if record else 0

    async def find_entities(
        self,
        names: list[str],
        collection: str = "default",
    ) -> list[GraphNode]:
        """Find entities by name."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity)
                WHERE e.name IN $names AND e.collection = $collection
                RETURN elementId(e) as id, e.name as name, e.type as type,
                       properties(e) as props
                """,
                names=names,
                collection=collection,
            )
            records = await result.data()
            return [
                GraphNode(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    properties={
                        k: v
                        for k, v in r["props"].items()
                        if k not in ("name", "type", "collection")
                    },
                )
                for r in records
            ]

    async def traverse(
        self,
        entity_names: list[str],
        max_hops: int = 3,
        collection: str = "default",
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """BFS traversal from starting entities up to max_hops."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (start:Entity)
                WHERE start.name IN $names AND start.collection = $collection
                CALL apoc.path.subgraphAll(start, {maxLevel: $max_hops})
                YIELD nodes, relationships
                UNWIND nodes AS n
                WITH collect(DISTINCT n) AS allNodes, relationships
                UNWIND allNodes AS node
                WITH collect({
                    id: elementId(node),
                    name: node.name,
                    type: node.type,
                    props: properties(node)
                }) AS nodeList, relationships
                UNWIND relationships AS rel
                RETURN nodeList,
                       collect(DISTINCT {
                           source: startNode(rel).name,
                           target: endNode(rel).name,
                           type: type(rel),
                           props: properties(rel)
                       }) AS edgeList
                """,
                names=entity_names,
                collection=collection,
                max_hops=max_hops,
            )
            record = await result.single()

            if not record:
                return [], []

            nodes = [
                GraphNode(
                    id=n["id"], name=n["name"], type=n["type"], properties=n["props"]
                )
                for n in record["nodeList"]
            ]
            edges = [
                GraphEdge(
                    source=e["source"],
                    target=e["target"],
                    type=e["type"],
                    properties=e["props"],
                )
                for e in record["edgeList"]
            ]
            return nodes, edges

    async def get_subgraph(
        self,
        collection: str = "default",
        center_entity: Optional[str] = None,
        depth: int = 2,
        limit: int = 100,
    ) -> dict:
        """Get graph data for visualization (Graph Explorer)."""
        async with self._driver.session() as session:
            if center_entity:
                result = await session.run(
                    """
                    MATCH (center:Entity {name: $entity, collection: $collection})
                    CALL apoc.path.subgraphAll(center, {maxLevel: $depth})
                    YIELD nodes, relationships
                    UNWIND nodes AS n
                    WITH collect(DISTINCT {
                        id: elementId(n), name: n.name, type: n.type
                    })[..$limit] AS nodeList, relationships
                    UNWIND relationships AS r
                    RETURN nodeList,
                           collect(DISTINCT {
                               source: elementId(startNode(r)),
                               target: elementId(endNode(r)),
                               type: type(r)
                           }) AS edgeList
                    """,
                    entity=center_entity,
                    collection=collection,
                    depth=depth,
                    limit=limit,
                )
            else:
                result = await session.run(
                    """
                    MATCH (n:Entity {collection: $collection})
                    WITH n LIMIT $limit
                    OPTIONAL MATCH (n)-[r]-(m:Entity {collection: $collection})
                    RETURN collect(DISTINCT {
                        id: elementId(n), name: n.name, type: n.type
                    }) AS nodeList,
                    collect(DISTINCT {
                        source: elementId(startNode(r)),
                        target: elementId(endNode(r)),
                        type: type(r)
                    }) AS edgeList
                    """,
                    collection=collection,
                    limit=limit,
                )

            record = await result.single()
            if not record:
                return {"nodes": [], "edges": []}

            return {
                "nodes": record["nodeList"],
                "edges": [e for e in record["edgeList"] if e["source"] and e["target"]],
            }

    async def delete_by_document(
        self,
        document_id: str,
        collection: str = "default",
    ) -> int:
        """Delete all entities and relationships for a given document_id.

        Returns count of deleted nodes.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {collection: $collection})
                WHERE e.document_id = $doc_id
                DETACH DELETE e
                RETURN count(e) as cnt
                """,
                doc_id=document_id,
                collection=collection,
            )
            record = await result.single()
            deleted = record["cnt"] if record else 0
            if deleted:
                logger.info(
                    "Deleted entities by document",
                    extra={
                        "document_id": document_id,
                        "collection": collection,
                        "count": deleted,
                    },
                )
            return deleted

    async def health_check(self) -> bool:
        """Check Neo4j connectivity."""
        try:
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False
