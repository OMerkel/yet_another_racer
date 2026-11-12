"""Tests for circuit geometry, reference landmarks, and lap sampling."""

import math
import unittest

from src.racer.game_state import new_game
from src.racer.track import (
    HOCKENHEIM,
    NURBURGRING_GP,
    TRACKS,
    TrackSegment,
    sample_track,
)


class TrackGeometryTests(unittest.TestCase):
    """Verify the closed, named Hockenheim circuit geometry."""

    def test_track_contains_all_named_sectors_and_matches_lap_length(
        self,
    ) -> None:
        """TST-017; FR-011.

        FEATURE: Hockenheim circuit geometry
        SCENARIO: Build the named sectors as a lap-length segment array
        GIVEN the deterministic circuit definition
        WHEN its segment metadata is inspected
        THEN all six requested sectors are represented
        AND segment lengths sum to the configured lap distance
        """
        sectors = {segment.sector for segment in HOCKENHEIM.segments}

        self.assertEqual(
            sectors,
            {
                "Start/finish",
                "Northern curve",
                "Parabolika",
                "Hairpin curve",
                "Motodrom",
                "Southern curve",
            },
        )
        sector_order: list[str] = []
        for segment in HOCKENHEIM.segments:
            if not sector_order or segment.sector != sector_order[-1]:
                sector_order.append(segment.sector)
        if sector_order[-1] == sector_order[0]:
            sector_order.pop()
        self.assertEqual(
            sector_order,
            [
                "Start/finish",
                "Northern curve",
                "Parabolika",
                "Hairpin curve",
                "Southern curve",
                "Motodrom",
                "Southern curve",
            ],
        )
        self.assertAlmostEqual(
            sum(segment.length for segment in HOCKENHEIM.segments),
            HOCKENHEIM.length,
        )
        hairpin_segments = [
            segment
            for segment in HOCKENHEIM.segments
            if segment.sector == "Hairpin curve"
        ]
        self.assertLess(
            max(abs(segment.curvature) for segment in hairpin_segments),
            0.1,
        )

    def test_track_sampling_is_continuous_across_the_start_finish_line(self):
        """TST-018; FR-011.

        FEATURE: Hockenheim circuit geometry
        SCENARIO: Wrap centerline sampling across the lap boundary
        GIVEN a closed circuit centerline
        WHEN positions immediately before and after the lap boundary are read
        THEN the sampled positions remain adjacent
        AND the full-lap sample matches the start sample
        """
        start = sample_track(0)
        before_start = sample_track(HOCKENHEIM.length - 0.01)
        gap = math.hypot(before_start.x - start.x, before_start.z - start.z)

        self.assertLess(gap, 0.1)
        self.assertEqual(sample_track(HOCKENHEIM.length), start)

    def test_nurburgring_track_has_named_sectors_and_wraps(self) -> None:
        """TST-022; FR-012.

        FEATURE: Nürburgring GP circuit geometry
        SCENARIO: Sample the second closed circuit independently
        GIVEN the Nürburgring GP track definition
        WHEN its sectors and lap boundary are inspected
        THEN its 5148-meter route has the named GP sections
        AND its final sample joins the start without a position jump
        """
        sectors = {segment.sector for segment in NURBURGRING_GP.segments}
        start = sample_track(0, NURBURGRING_GP)
        finish_approach = sample_track(
            NURBURGRING_GP.length - 100, NURBURGRING_GP
        )
        before_start = sample_track(
            NURBURGRING_GP.length - 0.01, NURBURGRING_GP
        )
        gap = math.hypot(before_start.x - start.x, before_start.z - start.z)

        self.assertEqual(NURBURGRING_GP.length, 5148.0)
        self.assertIsNot(NURBURGRING_GP, HOCKENHEIM)
        self.assertTrue(
            {
                "Castrol-S",
                "Mercedes Arena",
                "Ford-Kurve",
                "Dunlop-Kehre",
                "Michael-Schumacher-S",
                "Kumho-Kurve",
                "Bit-Kurve",
                "Hatzenbach-Bogen",
                "Veedol-Schikane",
                "Coca-Cola-Kurve",
            }.issubset(sectors)
        )
        bit_curve = [
            segment
            for segment in NURBURGRING_GP.segments
            if segment.sector == "Bit-Kurve"
        ]
        self.assertGreater(
            max(segment.z for segment in bit_curve),
            NURBURGRING_GP.bounds[3] - 1,
        )
        self.assertGreater(finish_approach.x, start.x + 5)
        self.assertLess(finish_approach.z, start.z - 5)
        castrol_s = [
            segment
            for segment in NURBURGRING_GP.segments
            if segment.sector == "Castrol-S"
        ]
        mercedes_arena = [
            segment
            for segment in NURBURGRING_GP.segments
            if segment.sector == "Mercedes Arena"
        ]
        self.assertGreater(
            max(segment.x for segment in castrol_s)
            - min(segment.x for segment in castrol_s),
            20,
        )
        self.assertLess(
            max(segment.z for segment in mercedes_arena),
            max(segment.z for segment in bit_curve) - 40,
        )
        dunlop_segments = [
            segment
            for segment in NURBURGRING_GP.segments
            if segment.sector == "Dunlop-Kehre"
        ]
        schumacher_segments = [
            segment
            for segment in NURBURGRING_GP.segments
            if segment.sector == "Michael-Schumacher-S"
        ]

        def orientation(
            first: TrackSegment,
            second: TrackSegment,
            third: TrackSegment,
        ) -> float:
            return (second.x - first.x) * (third.z - first.z) - (
                second.z - first.z
            ) * (third.x - first.x)

        crossings: list[tuple[TrackSegment, TrackSegment]] = []
        for first, following in zip(dunlop_segments, dunlop_segments[1:]):
            for second, next_segment in zip(
                schumacher_segments, schumacher_segments[1:]
            ):
                if (
                    orientation(first, following, second)
                    * orientation(first, following, next_segment)
                    < 0
                    and orientation(second, next_segment, first)
                    * orientation(second, next_segment, following)
                    < 0
                ):
                    crossings.append((first, second))
        self.assertFalse(crossings)
        min_x, max_x, min_z, max_z = NURBURGRING_GP.bounds
        width = max_x - min_x
        height = max_z - min_z
        landmarks = {
            "Dunlop-Kehre": ((36, 75), (50, 58), (46, 93)),
            "Mercedes Arena": ((605, 236), (578, 171), (527, 210)),
            "Veedol-Schikane": ((819, 376), (845, 383), (861, 396)),
        }
        for sector, points in landmarks.items():
            sector_segments = [
                segment
                for segment in NURBURGRING_GP.segments
                if segment.sector == sector
            ]
            for reference_x, reference_y in points:
                expected_x = (reference_x - 36) / (893 - 36)
                expected_z = (501 - reference_y) / (501 - 53)
                nearest = min(
                    math.hypot(
                        (segment.x - min_x) / width - expected_x,
                        (segment.z - min_z) / height - expected_z,
                    )
                    for segment in sector_segments
                )
                self.assertLess(nearest, 0.015, (sector, points))
        self.assertLess(gap, 0.1)

    def test_new_game_retains_the_selected_track(self):
        """TST-023; FR-012.

        FEATURE: Track selection
        SCENARIO: Start a race with the chosen circuit
        GIVEN the Nürburgring GP is selected before the race
        WHEN a fresh game state is created
        THEN the state retains that track for rendering and lap calculations
        """
        self.assertIs(new_game(NURBURGRING_GP).track, NURBURGRING_GP)

    def test_sample_heading_matches_centerline_and_is_continuous(self):
        """TST-028; FR-011, FR-012.

        FEATURE: Stable track geometry
        SCENARIO: Sample consistent position and tangent across segment joins
        GIVEN both closed GP centerlines
        WHEN positions and headings are sampled around each segment boundary
        THEN heading matches motion along the centerline without a jump
        """
        for track in TRACKS:
            for segment in track.segments:
                before = sample_track(segment.distance - 0.001, track)
                after = sample_track(segment.distance + 0.001, track)
                center = sample_track(segment.distance, track)
                tangent = math.atan2(after.x - before.x, after.z - before.z)
                angle = math.atan2(
                    math.sin(tangent - center.heading),
                    math.cos(tangent - center.heading),
                )
                jump = math.atan2(
                    math.sin(after.heading - before.heading),
                    math.cos(after.heading - before.heading),
                )
                self.assertLess(abs(angle), 0.01)
                self.assertLess(abs(jump), 0.02)

    def test_track_segments_store_curve_and_grade_data(self):
        """TST-019; FR-011.

        FEATURE: Hockenheim circuit geometry
        SCENARIO: Store geometric curve and elevation values per segment
        GIVEN the sampled circuit array
        WHEN segment geometry is inspected
        THEN the circuit has nonzero curvature and grade samples
        """
        self.assertTrue(
            any(
                abs(segment.curvature) > 0.0001
                for segment in HOCKENHEIM.segments
            )
        )
        self.assertTrue(
            any(abs(segment.grade) > 0.0001 for segment in HOCKENHEIM.segments)
        )


if __name__ == "__main__":
    unittest.main()
