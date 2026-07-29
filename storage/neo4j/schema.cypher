// Sejong City Cultural Heritage Service - Neo4j Cypher Graph Schema

// 1. Constraint Definitions for Node Keys
CREATE CONSTRAINT heritage_id_unique IF NOT EXISTS
FOR (h:Heritage) REQUIRE h.id IS UNIQUE;

CREATE CONSTRAINT category_name_unique IF NOT EXISTS
FOR (c:Category) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT era_name_unique IF NOT EXISTS
FOR (e:Era) REQUIRE e.name IS UNIQUE;

CREATE CONSTRAINT location_name_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.name IS UNIQUE;

CREATE CONSTRAINT course_id_unique IF NOT EXISTS
FOR (co:Course) REQUIRE co.id IS UNIQUE;

// 2. Sample Nodes & Relationship Creation Queries for Illustration

// Node Patterns:
// (:Heritage {id: 1, name: "비암사 극락보전", latitude: 36.5684, longitude: 127.2081, address: "세종특별자치시 전의면 비암사길 137"})
// (:Category {name: "유형문화재"})
// (:Era {name: "조선시대"})
// (:Location {name: "전의면"})
// (:Course {id: "uuid-1234", title: "세종 역사 도보 여행", theme: "역사 탐방"})

// Relationship Patterns:
// - Heritage belongs to a category
//   CREATE (h)-[:BELONGS_TO]->(c)
//
// - Heritage belongs to an historical era
//   CREATE (h)-[:FROM_ERA]->(e)
//
// - Heritage is located in a specific district
//   CREATE (h)-[:LOCATED_IN]->(l)
//
// - Spatial proximity connection (Next stops recommendation)
//   CREATE (h1)-[:NEXT_TO {distance_km: 15.4, travel_time_mins: 25}]->(h2)
//
// - User course visits a heritage site in a sequential order
//   CREATE (co)-[:VISITS {stop_order: 1}]->(h1)
//   CREATE (co)-[:VISITS {stop_order: 2}]->(h2)

// 3. Recommended Graph Queries for AI and Recommendations

// Find nearby heritage sites within the same era or category
// MATCH (h:Heritage)-[:FROM_ERA]->(e:Era)
// WHERE h.id = $current_id
// MATCH (recommend:Heritage)-[:FROM_ERA]->(e)
// WHERE recommend.id <> h.id
// RETURN recommend.name, recommend.address LIMIT 5;

// Retrieve the complete path of a custom course
// MATCH (c:Course {id: $course_id})-[r:VISITS]->(h:Heritage)
// RETURN h.name, r.stop_order ORDER BY r.stop_order ASC;
