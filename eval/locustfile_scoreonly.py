"""Score-only locustfile for clean latency baseline — excludes concurrent DB reads."""
import random
from locust import HttpUser, task, constant

_PURPOSES = ["car", "furniture/equipment", "radio/tv", "education", "business"]
_EMPLOYMENT = ["< 1 year", "1 <= X < 4 years", "4 <= X < 7 years", ">= 7 years"]


class ScoreOnlyUser(HttpUser):
    wait_time = constant(0)  # back-to-back requests

    @task
    def score(self):
        with self.client.post(
            "/api/score",
            json={
                "credit_amount": random.randint(500, 18000),
                "duration": random.choice([6, 12, 24, 36, 48]),
                "age": random.randint(20, 70),
                "purpose": random.choice(_PURPOSES),
                "employment": random.choice(_EMPLOYMENT),
                "installment_commitment": random.randint(1, 4),
                "existing_credits": random.randint(1, 4),
                "sex": random.randint(0, 1),
            },
            catch_response=True,
            timeout=30,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
