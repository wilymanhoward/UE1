# Last Seed - the shots of the opening cutscene.
#
# Purpose: one table that both ls_generate_intro.py (the music, timed to these shots) and build_level1_wildwood.py
# (which hands them to the opening AStoryTrigger) read, so the pictures and the music never drift apart.
# Each shot: (image number, seconds, start zoom, end zoom, start pan, end pan, fade-in seconds, flash, caption).
# Pan is a fraction of the screen, (x, y), positive to the right and down. A flash fades in from white.
# No dependencies, so it can be imported inside the editor.

SHOTS = [
    (1, 4.0, 1.03, 1.09, (0.0, 0.01), (0.0, 0.0), 0.8, False, ""),
    (2, 5.0, 1.05, 1.14, (0.0, 0.01), (0.0, 0.0), 0.35, False, "I knew every song in this forest."),
    (5, 6.0, 1.06, 1.17, (0.0, 0.0), (0.0, 0.01), 0.0, False, "The morning the witch came, the birds went quiet."),
    (7, 3.0, 1.14, 1.03, (0.0, 0.0), (0.0, 0.0), 0.0, True, ""),
    (9, 5.0, 1.07, 1.12, (0.02, 0.0), (-0.02, 0.0), 0.25, False, "Then the green faded from my leaves."),
    (11, 6.0, 1.04, 1.07, (0.0, 0.0), (0.0, 0.01), 0.0, False, "I felt the curse reach my roots."),
    (14, 5.0, 1.04, 1.1, (0.0, -0.01), (0.0, 0.02), 0.25, False, "I had just enough strength to let one seed fall."),
    (15, 8.0, 1.09, 1.01, (0.0, 0.0), (0.0, 0.0), 0.0, False, "That was you, little seed.\nGo on. Find a place to grow."),
]


def start_of(frame):
    """Seconds from the start of the cut to the given storyboard frame."""
    elapsed = 0.0
    for number, duration, *_ in SHOTS:
        if frame == number:
            return elapsed
        elapsed += duration
    raise ValueError(f"Frame {frame} is not in the intro cut")


TOTAL = sum(shot[1] for shot in SHOTS)

# The recording is premixed for this Sound Wave gain to leave room for the curse boom.
SOUNDTRACK_VOLUME = 2.5

