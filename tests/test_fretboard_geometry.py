"""Unit tests for the real geometry path; no camera or MediaPipe required."""
import pytest
from src.fretboard import Fretboard, FretboardGeom
from src import config


def make_geom():
    return FretboardGeom((100.,100.),(0.,1.),(1.,0.),6,4,20.,30.)


def test_geometry_has_six_strings_and_four_frets():
    geom=Fretboard().update([], (540,960))
    assert geom.n_strings==6 and geom.n_frets==4


def test_origin_is_first_cell():
    assert Fretboard().point_to_cell((100,100),make_geom())==(0,0)

@pytest.mark.parametrize('p',[(-1,100),(100,99),(251,100),(100,221),(10000,200)])
def test_outside_is_none(p):
    assert Fretboard().point_to_cell(p,make_geom()) is None


def test_all_six_strings():
    board=Fretboard(); g=make_geom()
    for s in range(6):
        assert board.point_to_cell((110,100+s*20+10),g)==(s,0)


def test_open_and_all_four_frets():
    board=Fretboard(); g=make_geom()
    for f in range(5):
        assert board.point_to_cell((100+f*30+15,115),g)==(0,f)


def test_centers_roundtrip():
    board=Fretboard(); g=make_geom()
    for s in range(6):
        for f in range(5):
            assert board.point_to_cell(board.cell_center((s,f),g),g)==(s,f)


def test_horizontal_right_hand_strum_line_is_independent():
    board=Fretboard();g=board.update([], (540,960))
    a,b=board.neck_line(g)
    assert a[1]==b[1] and b[0]>a[0]
    assert a[0] > g.origin[0] + g.fret_spacing*(g.n_frets+1)
