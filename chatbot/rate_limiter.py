"""Per-session rate limiter (SEC-6)."""
import time
from collections import deque
import config


class RateLimiter:
    def __init__(self, max_questions=None, window_minutes=None):
        self.max_q = max_questions or config.RATE_LIMIT_QUESTIONS
        self.window_s = (window_minutes or config.RATE_LIMIT_WINDOW_MIN) * 60
        self.questions = deque()

    def allow(self) -> tuple:
        now = time.time()
        while self.questions and self.questions[0] < now - self.window_s:
            self.questions.popleft()
        if len(self.questions) >= self.max_q:
            wait_s = int(self.questions[0] + self.window_s - now)
            return False, f"You've asked {self.max_q} questions recently. Please wait {wait_s} seconds before trying again."
        self.questions.append(now)
        return True, ""