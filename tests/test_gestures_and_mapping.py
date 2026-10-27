import pytest
from src import config
from src.demo import fake_hand
from src.chord_mapper import ChordMapper, finger_count_gesture

@pytest.mark.parametrize('count,chord',list(config.GESTURE_TO_CHORD.items()))
def test_six_gestures(count,chord):
    hand=fake_hand(180,160,role='Left',finger_count=count)
    assert finger_count_gesture(hand)==count
    assert ChordMapper().gesture(hand)[0]==chord


def test_chord_filter_waits_for_three_votes():
    mp=ChordMapper()
    assert mp.update_filtered('C') is None
    assert mp.update_filtered('C') is None
    assert mp.update_filtered('C')=='C'
    assert mp.update_filtered('Am')=='C'


def test_filter_loses_hand_after_dropout():
    mp=ChordMapper()
    for _ in range(5):mp.update_filtered('Em')
    for _ in range(5):mp.update_filtered(None)
    assert mp.update_filtered(None) is None


def test_single_note_semitone_mapping():
    mp=ChordMapper()
    assert mp.cells_to_notes([(0,0)])==[40]
    assert mp.cells_to_notes([(1,3)])==[48]
    assert mp.cells_to_notes([(5,4)])==[68]
    assert mp.cells_to_notes([(10,20)])==[]


def test_cell_filter():
    mp=ChordMapper()
    for _ in range(3):mp.update_cell((5,4))
    assert mp.update_cell((5,4))==(5,4)
    for _ in range(5):mp.update_cell(None)
    assert mp.update_cell(None) is None
