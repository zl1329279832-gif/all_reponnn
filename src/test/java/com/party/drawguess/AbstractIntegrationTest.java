package com.party.drawguess;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeAll;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.DynamicPropertyRegistry;

import java.io.File;
import java.nio.file.Files;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

@SpringBootTest
@AutoConfigureMockMvc
public abstract class AbstractIntegrationTest {

    @Autowired
    protected ObjectMapper objectMapper;

    private static File tempDb;

    @BeforeAll
    static void createTempDb() throws Exception {
        tempDb = Files.createTempFile("drawguess-test-", ".db").toFile();
        tempDb.deleteOnExit();
    }

    @DynamicPropertySource
    static void configureDataSource(DynamicPropertyRegistry registry) {
        if (tempDb == null) {
            try {
                tempDb = Files.createTempFile("drawguess-test-", ".db").toFile();
                tempDb.deleteOnExit();
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
        registry.add("spring.datasource.url", () -> "jdbc:sqlite:" + tempDb.getAbsolutePath());
    }

    protected Long registerPlayer(String openId, String nickname) throws Exception {
        String body = objectMapper.writeValueAsString(
                Map.of("openId", openId, "nickname", nickname));
        String resp = mockMvc().perform(post("/api/players/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andReturn().getResponse().getContentAsString();
        return extractDataId(resp);
    }

    protected org.springframework.test.web.servlet.MockMvc mockMvc() {
        return mockMvc;
    }

    @Autowired
    protected org.springframework.test.web.servlet.MockMvc mockMvc;

    protected String postJson(String path, Object payload) throws Exception {
        return mockMvc.perform(post(path)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andReturn().getResponse().getContentAsString();
    }

    protected String getJson(String path) throws Exception {
        return mockMvc.perform(get(path))
                .andReturn().getResponse().getContentAsString();
    }

    @SuppressWarnings("unchecked")
    protected Long extractDataId(String json) throws Exception {
        Map<String, Object> map = objectMapper.readValue(json, Map.class);
        Map<String, Object> data = (Map<String, Object>) map.get("data");
        Number id = (Number) data.get("id");
        if (id != null) return id.longValue();
        Number roomId = (Number) data.get("roomId");
        if (roomId != null) return roomId.longValue();
        throw new AssertionError("No id or roomId in response data: " + data);
    }

    @SuppressWarnings("unchecked")
    protected Map<String, Object> extractData(String json) throws Exception {
        Map<String, Object> map = objectMapper.readValue(json, Map.class);
        return (Map<String, Object>) map.get("data");
    }

    @SuppressWarnings("unchecked")
    protected int extractCode(String json) throws Exception {
        Map<String, Object> map = objectMapper.readValue(json, Map.class);
        return ((Number) map.get("code")).intValue();
    }
}
