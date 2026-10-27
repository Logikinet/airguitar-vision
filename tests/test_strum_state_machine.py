"""Strum state machine with synthetic deterministic time and pixel velocities."""
import pytest
from src.strum_detector import StrumDetector,StrumState,signed_distance

LINE=((0.,100.),(200.,100.))

def detector():return StrumDetector(v_th=.25,cooldown_ms=180,approach_margin=45,approach_timeout_ms=300)

def sample(d,y,vy,t):return d.update((80.,y),(0.,vy),LINE,t)


def test_initial_idle():
    assert detector().state==StrumState.IDLE


def test_missing_tip_is_idle():
    d=detector();assert d.update(None,None,LINE,5) is None
    assert d.state==StrumState.IDLE


def test_approach_without_cross():
    d=detector();assert sample(d,123.,-.19,20) is None
    assert d.state==StrumState.APPROACH


def test_crossing_emits_once_and_cooldown():
    d=detector()
    sample(d,123.,-.20,20)
    event=sample(d,93.,-.7,60)
    assert event and event.direction=='up'
    assert event.velocity==pytest.approx(.7)
    assert d.state==StrumState.COOLDOWN
    assert sample(d,110.,.8,70) is None
    assert sample(d,80.,-.8,100) is None


def test_downward_strum():
    d=detector(); sample(d,81.,.19,10)
    e=sample(d,112.,.60,50)
    assert e and e.direction=='down'


def test_cooldown_rearms_after_timeout():
    d=detector();sample(d,83.,.22,0)
    assert sample(d,115.,.70,45)
    sample(d,70.,-.6,150)
    assert sample(d,83.,.22,240) is None
    assert sample(d,110.,.8,270) is not None


def test_slow_motion_not_triggered():
    d=detector();sample(d,110.,-.08,0)
    assert sample(d,99.,-.10,90) is None


def test_leaving_neighborhood_resets():
    d=detector();sample(d,131.,-.18,0)
    assert d.state==StrumState.APPROACH
    sample(d,180.,.8,60)
    assert d.state==StrumState.IDLE


def test_approach_timeout():
    d=detector();sample(d,120.,-.18,0)
    assert d.state==StrumState.APPROACH
    sample(d,109.,-.10,310)
    assert d.state==StrumState.IDLE


def test_no_tip_resets_previous_crossing():
    d=detector();sample(d,120.,-.22,0)
    d.update(None,None,LINE,30)
    assert sample(d,90.,-.8,35) is None


def test_off_segment_never_triggers():
    d=detector()
    assert d.update((500.,95.),(0.,.9),LINE,20) is None
    assert d.state==StrumState.IDLE


def test_signed_distance():
    assert signed_distance((50,110),LINE)==pytest.approx(10)
    assert signed_distance((50,90),LINE)==pytest.approx(-10)
