import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.neo4j.driver.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class RedditLoader {

    private static final Logger logger = LoggerFactory.getLogger(RedditLoader.class);
    private static final String JSON_FILE_PATH = System.getenv("JSON_FILE_PATH");
    private static final String NEO4J_URI = System.getenv("NEO4J_URI");
    private static final String NEO4J_USER = System.getenv("NEO4J_USER");
    private static final String NEO4J_PASSWORD = System.getenv("NEO4J_PASSWORD");

    public static void main(String[] args) {
        if (JSON_FILE_PATH == null || NEO4J_URI == null) {
            logger.error("Missing environment variables. Set JSON_FILE_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD");
            System.exit(1);
        }

        try {
            File file = new File(JSON_FILE_PATH);
            if (!file.exists()) {
                throw new IOException("JSON file not found: " + JSON_FILE_PATH);
            }

            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(file);

            Driver driver = GraphDatabase.driver(NEO4J_URI, AuthTokens.basic(NEO4J_USER, NEO4J_PASSWORD));
            
            logger.info("Connected to Neo4j. Starting ingestion...");
            
            try (Session session = driver.session()) {
                // 1. Create Constraints
                createConstraints(session);

                // 2. Parse Data
                JsonNode postNode = root.get("post");
                JsonNode commentsNode = root.get("comments");

                // 3. Ingest
                ingestPost(session, postNode);
                ingestComments(session, commentsNode);
            }

            driver.close();
            logger.info("Ingestion completed successfully.");

        } catch (Exception e) {
            logger.error("Ingestion failed.", e);
            System.exit(1);
        }
    }

    private static void createConstraints(Session session) {
        String[] constraints = {
                "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Comment) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Subreddit) REQUIRE s.name IS UNIQUE"
        };

        for (String query : constraints) {
            try {
                session.run(query);
            } catch (Exception e) {
                logger.warn("Constraint issue (might already exist): {}", e.getMessage());
            }
        }
    }

    private static void ingestPost(Session session, JsonNode post) {
        String query = """
                MERGE (p:Post {id: $id})
                SET p.title = $title, p.text = $text, p.score = $score, p.url = $url, p.created_utc = $created_utc
                MERGE (s:Subreddit {name: $subreddit})
                MERGE (u:User {username: $author})
                MERGE (p)-[:BELONGS_TO]->(s)
                MERGE (u)-[:AUTHORED]->(p)
                """;

        Map<String, Object> params = Map.of(
                "id", post.get("id").asText(),
                "title", post.get("title").asText(),
                "text", post.get("text").asText(),
                "score", post.get("score").asInt(),
                "url", post.get("url").asText(),
                "created_utc", post.get("created_utc").asLong(),
                "subreddit", post.get("subreddit_name").asText(),
                "author", post.get("author").asText()
        );

        session.run(query, params);
        logger.info("Ingested Post: {}", post.get("id").asText());
    }

    private static void ingestComments(Session session, JsonNode comments) {
        if (comments == null || comments.isEmpty()) return;

        // Batch processing for performance
        List<JsonNode> commentList = comments.elements().collect(Collectors.toList());
        int batchSize = 500;

        for (int i = 0; i < commentList.size(); i += batchSize) {
            int end = Math.min(i + batchSize, commentList.size());
            List<JsonNode> chunk = commentList.subList(i, end);
            
            // Prepare parameters for the batch query
            List<Map<String, Object>> items = chunk.stream().map(c -> {
                Map<String, Object> item = new java.util.HashMap<>();
                item.put("id", c.get("id").asText());
                item.put("text", c.get("text").asText());
                item.put("score", c.get("score").asInt());
                item.put("created_utc", c.get("created_utc").asLong());
                item.put("author", c.get("author").asText());
                item.put("parent_id", c.get("parent_id").asText());
                return item;
            }).collect(Collectors.toList());

            // Cypher handles the relationship logic based on prefix
            String query = """
                UNWIND $items AS item
                MERGE (c:Comment {id: item.id})
                SET c.text = item.text, c.score = item.score, c.created_utc = item.created_utc
                
                MERGE (u:User {username: item.author})
                MERGE (u)-[:AUTHORED]->(c)
                
                // Determine Parent Relationship based on ID prefix (t3_ = Post, t1_ = Comment)
                FOREACH (ignore IN CASE WHEN item.parent_id STARTS WITH 't3_' THEN [1] ELSE [] END |
                    MERGE (p:Post {id: item.parent_id})
                    MERGE (c)-[:REPLIED_TO]->(p)
                )
                FOREACH (ignore IN CASE WHEN item.parent_id STARTS WITH 't1_' THEN [1] ELSE [] END |
                    MERGE (parent:Comment {id: item.parent_id})
                    MERGE (c)-[:REPLIED_TO]->(parent)
                )
                """;

            session.executeWrite(tx -> {
                tx.run(query, Map.of("items", items));
                return null;
            });

            logger.info("Ingested comment batch: {} to {}", i, end);
        }
    }
}
