"""Hand role mapping regression tests for mirrored camera labels."""
from src.hand_tracker import HandResult
from main import select_hand_roles


def hand(label: str) -> HandResult:
    return HandResult(label, [(0.0, 0.0, 0.0)] * 21, 0.99)

def test_normal_role_mapping_uses_left_label_for_chord():
    left, right = select_hand_roles([hand("Left"), hand("Right")], role_swap=False)
    assert left is not None and left.handedness == "Left"
    assert right is not None and right.handedness == "Right"

def test_corrected_mapping_swaps_reversed_detector_labels():
    # On the affected mirrored webcam, the physical left hand is reported as Right
    # and the physical right hand as Left, so the logical roles must be swapped.
    chord_hand, strum_hand = select_hand_roles([hand("Left"), hand("Right")], role_swap=True)
    assert chord_hand is not None and chord_hand.handedness == "Right"
    assert strum_hand is not None and strum_hand.handedness == "Left"
