"""GitHub webhook server - listens for PR events and triggers review pipeline.

Usage:
    acr webhook --port 8080 --secret your_webhook_secret

This starts a lightweight HTTP server that:
1. Listens for GitHub pull_request webhook events
2. Clones the PR branch
3. Runs the full Agent review pipeline
4. Posts review results as PR comments
"""
import os
import json
import hmac
import hashlib
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from agent_code_reviewer.config import Config
from agent_code_reviewer.orchestrator.director import Director

logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for GitHub webhook events."""

    config: Optional[Config] = None
    webhook_secret: str = ""

    def do_POST(self):
        """Handle incoming webhook POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Verify signature
        signature = self.headers.get("X-Hub-Signature-256", "")
        if self.webhook_secret and not self._verify_signature(body, signature):
            self._respond(403, {"error": "Invalid signature"})
            return

        # Parse event
        event = self.headers.get("X-GitHub-Event", "")
        if event != "pull_request":
            self._respond(200, {"status": "ignored", "event": event})
            return

        try:
            data = json.loads(body)
            action = data.get("action", "")
            pr = data.get("pull_request", {})

            # Only review on opened or synchronized events
            if action not in ("opened", "synchronize"):
                self._respond(200, {"status": "ignored", "action": action})
                return

            repo_url = pr.get("head", {}).get("repo", {}).get("clone_url", "")
            pr_title = pr.get("title", "")
            pr_body = pr.get("body", "") or ""
            pr_number = pr.get("number", 0)
            repo_name = data.get("repository", {}).get("full_name", "")

            if not repo_url:
                self._respond(400, {"error": "No clone URL found"})
                return

            # Build requirement from PR info
            requirement = f"审查 PR #{pr_number}: {pr_title}\n\n{pr_body[:500]}"

            logger.info(f"Starting review for PR #{pr_number} on {repo_name}")

            # Run review in background thread
            import threading
            thread = threading.Thread(
                target=self._run_review,
                args=(repo_url, requirement, repo_name, pr_number),
                daemon=True,
            )
            thread.start()

            self._respond(200, {"status": "processing", "pr": pr_number})

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self._respond(500, {"error": str(e)})

    def _run_review(self, repo_url: str, requirement: str, repo_name: str, pr_number: int):
        """Run the review pipeline in a background thread."""
        try:
            director = Director(self.config)
            report = director.run(
                user_requirement=requirement,
                repo_url=repo_url,
            )

            # Save report locally
            from agent_code_reviewer.report.formatter import save_report
            output_dir = f"reports/{repo_name.replace('/', '_')}/PR-{pr_number}"
            saved = save_report(report, output_dir)

            logger.info(f"Review complete for PR #{pr_number}: {saved}")

        except Exception as e:
            logger.error(f"Review failed for PR #{pr_number}: {e}")

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature."""
        if not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _respond(self, status: int, data: dict):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        logger.info(f"Webhook: {format % args}")


def start_webhook_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    secret: str = "",
    config: Optional[Config] = None,
):
    """Start the webhook server.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        secret: GitHub webhook secret for signature verification.
        config: Application configuration.
    """
    WebhookHandler.webhook_secret = secret
    WebhookHandler.config = config or Config.load()

    server = HTTPServer((host, port), WebhookHandler)
    logger.info(f"Webhook server listening on {host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down webhook server...")
        server.shutdown()
