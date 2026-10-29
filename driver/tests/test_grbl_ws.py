from qubot_drivers.move.grbl_ws import GrblWSController


def test_multiline_frame_detects_ok_response():
    frame = "<Idle|MPos:0.000,0.000,0.000>\r\nok\r\n"

    assert GrblWSController._message_has_command_response(frame)


def test_status_only_frame_is_not_a_command_response():
    frame = "<Idle|MPos:0.000,0.000,0.000>\r\n"

    assert not GrblWSController._message_has_command_response(frame)
