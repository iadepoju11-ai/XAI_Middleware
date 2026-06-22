"""
Locust load test — Phase 8 quantitative evaluation.

Target: POST /api/score at 1000 concurrent users, 10-minute run.
NFR: p95 latency < 500ms, 0% timeout rate.

Run from project root:
    cd eval
    locust -f locustfile.py --headless -u 1000 -r 50 -t 10m \
           --host http://localhost:5000 \
           --html locust_report.html \
           --csv locust_results

Quick smoke (50 users, 60s):
    locust -f locustfile.py --headless -u 50 -r 10 -t 60s \
           --host http://localhost:5000

Requirements:
    - Flask API must be running: cd backend && python app.py
    - Install: pip install locust (already in requirements.txt)
"""
import random

from locust import HttpUser, task, between


# Realistic feature distributions drawn from German Credit dataset statistics
_PURPOSES = ["car", "furniture/equipment", "radio/tv", "domestic appliance",
             "repairs", "education", "vacation", "retraining", "business", "other"]
_EMPLOYMENT = ["unemployed", "< 1 year", "1 <= X < 4 years", "4 <= X < 7 years", ">= 7 years"]


def _random_payload():
    return {
        "credit_amount": random.randint(500, 18_000),
        "duration":      random.choice([6, 12, 18, 24, 36, 48, 60]),
        "age":           random.randint(19, 75),
        "purpose":       random.choice(_PURPOSES),
        "employment":    random.choice(_EMPLOYMENT),
        "installment_commitment": random.randint(1, 4),
        "existing_credits":       random.randint(1, 4),
        "sex":                    random.randint(0, 1),
    }


class CreditScoringUser(HttpUser):
    wait_time = between(0.1, 0.5)   # short think-time to stress-test the pipeline

    @task(10)
    def score(self):
        """Primary workload: credit scoring pipeline."""
        with self.client.post(
            "/api/score",
            json=_random_payload(),
            catch_response=True,
            timeout=30,
        ) as response:
            if response.status_code != 200:
                response.failure(f"score returned {response.status_code}")
            elif "application_id" not in response.text:
                response.failure("response missing application_id")

    @task(2)
    def audit_list(self):
        """Secondary workload: audit trail reads (paginated)."""
        page = random.randint(1, 5)
        with self.client.get(
            f"/api/audit?page={page}&page_size=20",
            catch_response=True,
            timeout=30,
        ) as response:
            if response.status_code != 200:
                response.failure(f"audit list returned {response.status_code}")

    @task(1)
    def fairness(self):
        """Background probe: fairness metrics endpoint."""
        self.client.get("/api/fairness", timeout=30)

    @task(1)
    def health(self):
        """Heartbeat: system health endpoint."""
        self.client.get("/api/health", timeout=30)
