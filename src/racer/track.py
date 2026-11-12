"""Deterministic centerline geometry for the Hockenheim GP circuit."""

import math
from bisect import bisect_right
from dataclasses import dataclass

_SAMPLES_PER_SPAN = 10
ROAD_HALF_WIDTH = 6.5


@dataclass(frozen=True)
class TrackSegment:
    """One sampled piece of circuit geometry in world coordinates."""

    distance: float
    length: float
    x: float
    z: float
    heading: float
    curvature: float
    elevation: float
    grade: float
    sector: str


@dataclass(frozen=True)
class TrackSample:
    """Interpolated centerline data at a race distance."""

    x: float
    z: float
    heading: float
    curvature: float
    elevation: float
    grade: float
    sector: str


@dataclass(frozen=True)
class Track:
    """Circuit geometry and lookup data for one selectable track."""

    name: str
    length: float
    segments: tuple[TrackSegment, ...]
    segment_starts: tuple[float, ...]
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class _Waypoint:
    x: float
    z: float
    sector: str
    elevation: float


_HOCKENHEIM_WAYPOINTS = (
    _Waypoint(302, -239, "Start/finish", 99),
    _Waypoint(300, -218, "Start/finish", 100),
    _Waypoint(258, -195, "Northern curve", 101),
    _Waypoint(258, -175, "Northern curve", 102),
    _Waypoint(298, -120, "Northern curve", 103),
    _Waypoint(365, -60, "Northern curve", 104),
    _Waypoint(415, -30, "Northern curve", 103),
    _Waypoint(432, -48, "Northern curve", 102),
    _Waypoint(432, -75, "Northern curve", 101),
    _Waypoint(450, -100, "Parabolika", 100),
    _Waypoint(540, -150, "Parabolika", 99),
    _Waypoint(650, -171, "Parabolika", 98),
    _Waypoint(745, -164, "Parabolika", 99),
    _Waypoint(845, -140, "Parabolika", 100),
    _Waypoint(858, -140, "Hairpin curve", 101),
    _Waypoint(864, -142, "Hairpin curve", 102),
    _Waypoint(869, -147, "Hairpin curve", 103),
    _Waypoint(872, -153, "Hairpin curve", 104),
    _Waypoint(872, -160, "Hairpin curve", 104),
    _Waypoint(869, -166, "Hairpin curve", 103),
    _Waypoint(864, -171, "Hairpin curve", 102),
    _Waypoint(857, -173, "Hairpin curve", 101),
    _Waypoint(849, -172, "Hairpin curve", 100),
    _Waypoint(840, -169, "Hairpin curve", 100),
    _Waypoint(830, -166, "Hairpin curve", 101),
    _Waypoint(817, -169, "Hairpin curve", 102),
    _Waypoint(800, -177, "Hairpin curve", 102),
    _Waypoint(780, -195, "Hairpin curve", 102),
    _Waypoint(705, -228, "Southern curve", 101),
    _Waypoint(650, -215, "Southern curve", 100),
    _Waypoint(607, -205, "Southern curve", 99),
    _Waypoint(586, -220, "Southern curve", 99),
    _Waypoint(588, -245, "Southern curve", 100),
    _Waypoint(606, -270, "Southern curve", 101),
    _Waypoint(575, -305, "Southern curve", 102),
    _Waypoint(510, -340, "Southern curve", 103),
    _Waypoint(477, -354, "Motodrom", 104),
    _Waypoint(430, -368, "Motodrom", 105),
    _Waypoint(398, -350, "Motodrom", 104),
    _Waypoint(370, -306, "Motodrom", 103),
    _Waypoint(342, -274, "Motodrom", 102),
    _Waypoint(329, -292, "Motodrom", 101),
    _Waypoint(347, -325, "Motodrom", 100),
    _Waypoint(368, -360, "Southern curve", 99),
    _Waypoint(395, -405, "Southern curve", 98),
    _Waypoint(385, -428, "Southern curve", 98),
    _Waypoint(358, -427, "Southern curve", 99),
    _Waypoint(337, -400, "Southern curve", 100),
    _Waypoint(319, -347, "Start/finish", 101),
    _Waypoint(302, -289, "Start/finish", 100),
    _Waypoint(302, -263, "Start/finish", 99),
)

_NURBURGRING_WAYPOINTS = (
    _Waypoint(650, -355, "Start/finish", 300),
    _Waypoint(610, -326, "Start/finish", 301),
    _Waypoint(566, -296, "Start/finish", 302),
    _Waypoint(535, -275, "Castrol-S", 303),
    _Waypoint(524, -264, "Castrol-S", 304),
    _Waypoint(522, -255, "Castrol-S", 305),
    _Waypoint(529, -247, "Castrol-S", 304),
    _Waypoint(545, -244, "Mercedes Arena", 303),
    _Waypoint(578, -246, "Mercedes Arena", 302),
    _Waypoint(597, -244, "Mercedes Arena", 301),
    _Waypoint(605, -236, "Mercedes Arena", 300),
    _Waypoint(606, -226, "Mercedes Arena", 299),
    _Waypoint(601, -208, "Mercedes Arena", 298),
    _Waypoint(594, -189, "Mercedes Arena", 299),
    _Waypoint(587, -175, "Mercedes Arena", 300),
    _Waypoint(578, -171, "Mercedes Arena", 301),
    _Waypoint(569, -176, "Mercedes Arena", 302),
    _Waypoint(570, -187, "Mercedes Arena", 303),
    _Waypoint(573, -198, "Mercedes Arena", 304),
    _Waypoint(566, -204, "Mercedes Arena", 303),
    _Waypoint(548, -209, "Mercedes Arena", 302),
    _Waypoint(527, -210, "Mercedes Arena", 301),
    _Waypoint(491, -200, "Ford-Kurve", 300),
    _Waypoint(445, -193, "Ford-Kurve", 299),
    _Waypoint(395, -186, "Ford-Kurve", 298),
    _Waypoint(345, -179, "Ford-Kurve", 299),
    _Waypoint(316, -175, "Ford-Kurve", 300),
    _Waypoint(298, -181, "Ford-Kurve", 301),
    _Waypoint(287, -197, "Ford-Kurve", 302),
    _Waypoint(280, -223, "Ford-Kurve", 303),
    _Waypoint(273, -243, "Ford-Kurve", 304),
    _Waypoint(262, -251, "Ford-Kurve", 303),
    _Waypoint(248, -251, "Ford-Kurve", 302),
    _Waypoint(237, -243, "Dunlop-Kehre", 301),
    _Waypoint(219, -217, "Dunlop-Kehre", 300),
    _Waypoint(193, -187, "Dunlop-Kehre", 299),
    _Waypoint(164, -158, "Dunlop-Kehre", 298),
    _Waypoint(132, -135, "Dunlop-Kehre", 299),
    _Waypoint(102, -117, "Dunlop-Kehre", 300),
    _Waypoint(72, -104, "Dunlop-Kehre", 301),
    _Waypoint(46, -93, "Dunlop-Kehre", 302),
    _Waypoint(37, -84, "Dunlop-Kehre", 303),
    _Waypoint(36, -75, "Dunlop-Kehre", 304),
    _Waypoint(40, -64, "Dunlop-Kehre", 303),
    _Waypoint(50, -58, "Dunlop-Kehre", 302),
    _Waypoint(61, -59, "Dunlop-Kehre", 301),
    _Waypoint(79, -71, "Michael-Schumacher-S", 300),
    _Waypoint(110, -94, "Michael-Schumacher-S", 299),
    _Waypoint(142, -117, "Michael-Schumacher-S", 298),
    _Waypoint(174, -138, "Michael-Schumacher-S", 299),
    _Waypoint(192, -145, "Michael-Schumacher-S", 300),
    _Waypoint(207, -146, "Michael-Schumacher-S", 301),
    _Waypoint(228, -140, "Michael-Schumacher-S", 302),
    _Waypoint(251, -130, "Michael-Schumacher-S", 303),
    _Waypoint(269, -126, "Michael-Schumacher-S", 302),
    _Waypoint(299, -129, "Michael-Schumacher-S", 301),
    _Waypoint(350, -136, "Michael-Schumacher-S", 300),
    _Waypoint(409, -144, "Michael-Schumacher-S", 301),
    _Waypoint(466, -152, "Kumho-Kurve", 302),
    _Waypoint(480, -145, "Kumho-Kurve", 303),
    _Waypoint(487, -124, "Kumho-Kurve", 304),
    _Waypoint(495, -92, "Kumho-Kurve", 305),
    _Waypoint(504, -67, "Bit-Kurve", 306),
    _Waypoint(516, -55, "Bit-Kurve", 305),
    _Waypoint(531, -53, "Bit-Kurve", 304),
    _Waypoint(549, -60, "Bit-Kurve", 303),
    _Waypoint(590, -84, "Bit-Kurve", 302),
    _Waypoint(645, -116, "Bit-Kurve", 301),
    _Waypoint(702, -149, "Hatzenbach-Bogen", 300),
    _Waypoint(716, -165, "Hatzenbach-Bogen", 299),
    _Waypoint(735, -205, "Hatzenbach-Bogen", 298),
    _Waypoint(759, -258, "Hatzenbach-Bogen", 299),
    _Waypoint(783, -311, "Hatzenbach-Bogen", 300),
    _Waypoint(806, -361, "Hatzenbach-Bogen", 301),
    _Waypoint(819, -376, "Veedol-Schikane", 302),
    _Waypoint(829, -381, "Veedol-Schikane", 303),
    _Waypoint(845, -383, "Veedol-Schikane", 302),
    _Waypoint(854, -387, "Veedol-Schikane", 301),
    _Waypoint(861, -396, "Veedol-Schikane", 300),
    _Waypoint(873, -425, "Coca-Cola-Kurve", 301),
    _Waypoint(884, -455, "Coca-Cola-Kurve", 302),
    _Waypoint(893, -480, "Coca-Cola-Kurve", 303),
    _Waypoint(892, -489, "Coca-Cola-Kurve", 302),
    _Waypoint(881, -498, "Coca-Cola-Kurve", 301),
    _Waypoint(869, -501, "Coca-Cola-Kurve", 300),
    _Waypoint(850, -495, "Coca-Cola-Kurve", 299),
    _Waypoint(818, -474, "Start/finish", 298),
    _Waypoint(770, -440, "Start/finish", 299),
    _Waypoint(720, -405, "Start/finish", 300),
    _Waypoint(680, -376, "Start/finish", 301),
)


def _spline_value(
    p0: float,
    p1: float,
    p2: float,
    p3: float,
    t: float,
    knots: tuple[float, float, float, float],
) -> float:
    """Evaluate one centripetal Catmull-Rom spline component."""
    knot0, knot1, knot2, knot3 = knots
    interval = knot2 - knot1
    tangent1 = (p2 - p0) * interval / (knot2 - knot0)
    tangent2 = (p3 - p1) * interval / (knot3 - knot1)
    squared = t * t
    cubed = squared * t
    return (
        (2 * cubed - 3 * squared + 1) * p1
        + (cubed - 2 * squared + t) * tangent1
        + (-2 * cubed + 3 * squared) * p2
        + (cubed - squared) * tangent2
    )


def _build_segments(
    waypoints: tuple[_Waypoint, ...], track_length: float
) -> tuple[TrackSegment, ...]:
    samples: list[tuple[float, float, float, str]] = []
    waypoint_count = len(waypoints)
    for index, point in enumerate(waypoints):
        previous = waypoints[(index - 1) % waypoint_count]
        following = waypoints[(index + 1) % waypoint_count]
        after_following = waypoints[(index + 2) % waypoint_count]
        first_interval = math.sqrt(
            math.hypot(point.x - previous.x, point.z - previous.z)
        )
        second_interval = math.sqrt(
            math.hypot(following.x - point.x, following.z - point.z)
        )
        third_interval = math.sqrt(
            math.hypot(
                after_following.x - following.x,
                after_following.z - following.z,
            )
        )
        knots = (
            0.0,
            first_interval,
            first_interval + second_interval,
            first_interval + second_interval + third_interval,
        )
        for sample_index in range(_SAMPLES_PER_SPAN):
            t = sample_index / _SAMPLES_PER_SPAN
            samples.append(
                (
                    _spline_value(
                        previous.x,
                        point.x,
                        following.x,
                        after_following.x,
                        t,
                        knots,
                    ),
                    _spline_value(
                        previous.z,
                        point.z,
                        following.z,
                        after_following.z,
                        t,
                        knots,
                    ),
                    _spline_value(
                        previous.elevation,
                        point.elevation,
                        following.elevation,
                        after_following.elevation,
                        t,
                        knots,
                    ),
                    point.sector,
                )
            )

    raw_lengths = tuple(
        math.hypot(
            samples[(index + 1) % len(samples)][0] - sample[0],
            samples[(index + 1) % len(samples)][1] - sample[1],
        )
        for index, sample in enumerate(samples)
    )
    scale = track_length / sum(raw_lengths)
    headings = tuple(
        math.atan2(
            samples[(index + 1) % len(samples)][0]
            - samples[(index - 1) % len(samples)][0],
            samples[(index + 1) % len(samples)][1]
            - samples[(index - 1) % len(samples)][1],
        )
        for index in range(len(samples))
    )

    segments: list[TrackSegment] = []
    distance = 0.0
    for index, sample in enumerate(samples):
        next_index = (index + 1) % len(samples)
        length = raw_lengths[index] * scale
        heading_delta = math.atan2(
            math.sin(headings[next_index] - headings[index]),
            math.cos(headings[next_index] - headings[index]),
        )
        next_sample = samples[next_index]
        segments.append(
            TrackSegment(
                distance=distance,
                length=length,
                x=sample[0] * scale,
                z=sample[1] * scale,
                heading=headings[index],
                curvature=heading_delta / length,
                elevation=sample[2],
                grade=(next_sample[2] - sample[2]) / length,
                sector=sample[3],
            )
        )
        distance += length
    return tuple(segments)


def _make_track(
    name: str, length: float, waypoints: tuple[_Waypoint, ...]
) -> Track:
    segments = _build_segments(waypoints, length)
    bounds = (
        min(segment.x for segment in segments),
        max(segment.x for segment in segments),
        min(segment.z for segment in segments),
        max(segment.z for segment in segments),
    )
    return Track(
        name=name,
        length=length,
        segments=segments,
        segment_starts=tuple(segment.distance for segment in segments),
        bounds=bounds,
    )


HOCKENHEIM = _make_track("HOCKENHEIMRING", 4574.0, _HOCKENHEIM_WAYPOINTS)
NURBURGRING_GP = _make_track("NURBURGRING GP", 5148.0, _NURBURGRING_WAYPOINTS)
TRACKS = (HOCKENHEIM, NURBURGRING_GP)
DEFAULT_TRACK: Track = HOCKENHEIM


def sample_track(distance: float, track: Track = DEFAULT_TRACK) -> TrackSample:
    """Sample the closed circuit at a wrapped race distance."""
    wrapped_distance = distance % track.length
    index = bisect_right(track.segment_starts, wrapped_distance) - 1
    segment = track.segments[index]
    next_segment = track.segments[(index + 1) % len(track.segments)]
    progress = (wrapped_distance - segment.distance) / segment.length

    length = segment.length
    tangent_x = math.sin(segment.heading) * length
    tangent_z = math.cos(segment.heading) * length
    next_tangent_x = math.sin(next_segment.heading) * length
    next_tangent_z = math.cos(next_segment.heading) * length
    squared = progress * progress
    cubed = squared * progress

    def component(
        start: float, end: float, tangent: float, next_tangent: float
    ) -> tuple[float, float, float]:
        value = (
            (2 * cubed - 3 * squared + 1) * start
            + (cubed - 2 * squared + progress) * tangent
            + (-2 * cubed + 3 * squared) * end
            + (cubed - squared) * next_tangent
        )
        first = (
            (6 * squared - 6 * progress) * start
            + (3 * squared - 4 * progress + 1) * tangent
            + (-6 * squared + 6 * progress) * end
            + (3 * squared - 2 * progress) * next_tangent
        )
        second = (
            (12 * progress - 6) * start
            + (6 * progress - 4) * tangent
            + (-12 * progress + 6) * end
            + (6 * progress - 2) * next_tangent
        )
        return value, first, second

    world_x, first_x, second_x = component(
        segment.x, next_segment.x, tangent_x, next_tangent_x
    )
    world_z, first_z, second_z = component(
        segment.z, next_segment.z, tangent_z, next_tangent_z
    )
    derivative_length = math.hypot(first_x, first_z)
    return TrackSample(
        x=world_x,
        z=world_z,
        heading=math.atan2(first_x, first_z),
        curvature=(first_z * second_x - first_x * second_z)
        / max(derivative_length**3, 1e-12),
        elevation=segment.elevation
        + (next_segment.elevation - segment.elevation) * progress,
        grade=segment.grade,
        sector=segment.sector,
    )
