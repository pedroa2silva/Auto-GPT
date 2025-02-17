import contextlib
import os
from functools import wraps
from typing import Any, Callable, Optional

import pytest

from tests.integration.challenges.challenge_decorator.challenge import Challenge
from tests.integration.challenges.challenge_decorator.challenge_utils import (
    create_challenge,
)
from tests.integration.challenges.challenge_decorator.score_utils import (
    get_scores,
    update_new_score,
)

MAX_LEVEL_TO_IMPROVE_ON = (
    1  # we will attempt to beat 1 level above the current level for now.
)


def challenge(func: Callable[..., Any]) -> Callable[..., None]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        run_remaining = MAX_LEVEL_TO_IMPROVE_ON if Challenge.BEAT_CHALLENGES else 1

        while run_remaining > 0:
            current_score, new_score, new_score_location = get_scores()
            level_to_run = kwargs["level_to_run"] if "level_to_run" in kwargs else None
            challenge = create_challenge(
                func, current_score, Challenge.BEAT_CHALLENGES, level_to_run
            )
            if challenge.level_to_run is not None:
                kwargs["level_to_run"] = challenge.level_to_run
                with contextlib.suppress(AssertionError):
                    func(*args, **kwargs)
                    challenge.succeeded = True
            else:
                challenge.skipped = True
            if os.environ.get("CI") == "true":
                new_max_level_beaten = get_new_max_level_beaten(
                    challenge, Challenge.BEAT_CHALLENGES
                )
                update_new_score(
                    new_score_location, new_score, challenge, new_max_level_beaten
                )
            if challenge.level_to_run is None:
                pytest.skip("This test has not been unlocked yet.")

            if not challenge.succeeded:
                if Challenge.BEAT_CHALLENGES or challenge.is_new_challenge:
                    # xfail
                    pytest.xfail("Challenge failed")
                raise AssertionError("Challenge failed")
            run_remaining -= 1

    return wrapper


def get_new_max_level_beaten(
    challenge: Challenge, beat_challenges: bool
) -> Optional[int]:
    if challenge.succeeded:
        return challenge.level_to_run
    if challenge.skipped:
        return challenge.max_level_beaten
    # Challenge failed
    return challenge.max_level_beaten if beat_challenges else None
