import json
import unittest
from unittest.mock import Mock, patch

from orchestrator_api import DECISION_SCHEMA, app, classify_task


class OrchestratorApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @staticmethod
    def model_response(agent, reason="clasificación de prueba"):
        response = Mock()
        response.json.return_value = {
            "response": json.dumps({"agent": agent, "reason": reason})
        }
        response.raise_for_status.return_value = None
        return response

    def test_routes_trace_analysis_to_agent(self):
        agent_response = Mock()
        agent_response.status_code = 200
        agent_response.json.return_value = {"status": "success", "diagnostic_report": "OK"}
        agent_response.raise_for_status.return_value = None

        with patch("orchestrator_api.requests.post", side_effect=[
            self.model_response("log-analyzer-agent"), agent_response
        ]) as post:
            response = self.client.post("/api/orchestrate", json={
                "task": "Analiza estas trazas",
                "logs": "[ERROR] Database timeout",
                "use_cache": False,
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["decision"]["agent"], "log-analyzer-agent")
        self.assertEqual(response.json["agent_result"]["status"], "success")
        self.assertEqual(post.call_args_list[1].kwargs["json"], {
            "logs": "[ERROR] Database timeout",
            "use_cache": False,
        })

    def test_normalizes_trace_agent_alias_and_uses_schema(self):
        with patch("orchestrator_api.requests.post", return_value=self.model_response("Agente de trazas")) as post:
            decision = classify_task("Analiza estos logs", logs_provided=True)

        self.assertEqual(decision["agent"], "log-analyzer-agent")
        self.assertEqual(post.call_args.kwargs["json"]["format"], DECISION_SCHEMA)

    def test_sends_cloud_api_key_as_bearer_token(self):
        with patch("orchestrator_api.OLLAMA_API_KEY", "test-cloud-key"):
            with patch("orchestrator_api.requests.post", return_value=self.model_response("none")) as post:
                classify_task("Escribe un poema", logs_provided=False)

        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-cloud-key")

    def test_health_reports_cloud_settings_without_revealing_key(self):
        with patch("orchestrator_api.OLLAMA_API_URL", "https://api.ollama.com"), \
                patch("orchestrator_api.OLLAMA_API_KEY", "secret-test-key"), \
                patch("orchestrator_api.ORCHESTRATOR_MODEL", "llama3.2:1b:cloud"):
            response = self.client.get("/api/health")

        self.assertEqual(response.json["ollama_provider"], "cloud")
        self.assertEqual(response.json["model"], "llama3.2:1b:cloud")
        self.assertTrue(response.json["api_key_configured"])
        self.assertNotIn("secret-test-key", response.get_data(as_text=True))

    def test_cloud_request_uses_cloud_endpoint(self):
        with patch("orchestrator_api.OLLAMA_API_URL", "https://api.ollama.com"), \
                patch("orchestrator_api.requests.post", return_value=self.model_response("none")) as post:
            classify_task("Escribe un poema", logs_provided=False)

        self.assertEqual(post.call_args.args[0], "https://api.ollama.com/api/generate")

    def test_rejects_unrecognized_agent_name(self):
        with patch("orchestrator_api.requests.post", return_value=self.model_response("api-design-agent")):
            with self.assertRaisesRegex(ValueError, "agente no permitido"):
                classify_task("Analiza estos logs", logs_provided=True)

    def test_does_not_call_agent_for_unmatched_task(self):
        with patch("orchestrator_api.requests.post", return_value=self.model_response("none")) as post:
            response = self.client.post("/api/orchestrate", json={"task": "Escribe un poema"})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json["status"], "unrouted")
        post.assert_called_once()

    def test_preserves_agent_error_status(self):
        agent_response = Mock()
        agent_response.status_code = 400
        agent_response.json.return_value = {"status": "error", "step": "1_ingestion"}

        with patch("orchestrator_api.requests.post", side_effect=[
            self.model_response("log-analyzer-agent"), agent_response
        ]):
            response = self.client.post("/api/orchestrate", json={
                "task": "Analiza logs",
                "logs": "",
            })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "agent_error")

    def test_requires_task_or_logs(self):
        response = self.client.post("/api/orchestrate", json={})

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()