"""Test the stream worker corner cases.

Exercise the stream worker functionality by mocking av.open calls to return a
fake media container as well a fake decoded stream in the form of a series of
packets. This is needed as some of these cases can't be encoded using pyav.  It
is preferred to use test_hls.py for example, when possible.

The worker opens the stream source (typically a URL) and gets back a
container that has audio/video streams. The worker iterates over the sequence
of packets and sends them to the appropriate output buffers. Each test
creates a packet sequence, with a mocked output buffer to capture the segments
pushed to the output streams. The packet sequence can be used to exercise
failure modes or corner cases like how out of order packets are handled.
"""

import fractions
import io
import math
import threading
from unittest.mock import patch

import av

from homeassistant.components.stream import Stream, create_stream
from homeassistant.components.stream.const import (
    HLS_PROVIDER,
    MAX_MISSING_DTS,
    PACKETS_TO_WAIT_FOR_AUDIO,
    TARGET_SEGMENT_DURATION,
)
from homeassistant.components.stream.worker import SegmentBuffer, stream_worker
from homeassistant.setup import async_setup_component

from tests.components.stream.common import generate_h264_video

STREAM_SOURCE = "some-stream-source"
# Formats here are arbitrary, not exercised by tests
AUDIO_STREAM_FORMAT = "mp3"
VIDEO_STREAM_FORMAT = "h264"
VIDEO_FRAME_RATE = 12
AUDIO_SAMPLE_RATE = 11025
KEYFRAME_INTERVAL = 1  # in seconds
PACKET_DURATION = fractions.Fraction(1, VIDEO_FRAME_RATE)  # in seconds
SEGMENT_DURATION = (
    math.ceil(TARGET_SEGMENT_DURATION / KEYFRAME_INTERVAL) * KEYFRAME_INTERVAL
)  # in seconds
TEST_SEQUENCE_LENGTH = 5 * VIDEO_FRAME_RATE
LONGER_TEST_SEQUENCE_LENGTH = 20 * VIDEO_FRAME_RATE
OUT_OF_ORDER_PACKET_INDEX = 3 * VIDEO_FRAME_RATE
PACKETS_PER_SEGMENT = SEGMENT_DURATION / PACKET_DURATION
SEGMENTS_PER_PACKET = PACKET_DURATION / SEGMENT_DURATION
TIMEOUT = 15


class FakePyAvStream:
    """A fake pyav Stream."""

    def __init__(self, name, rate):
        """Initialize the stream."""
        self.name = name
        self.time_base = fractions.Fraction(1, rate)
        self.profile = "ignored-profile"

        class FakeCodec:
            name = "aac"

        self.codec = FakeCodec()


VIDEO_STREAM = FakePyAvStream(VIDEO_STREAM_FORMAT, VIDEO_FRAME_RATE)
AUDIO_STREAM = FakePyAvStream(AUDIO_STREAM_FORMAT, AUDIO_SAMPLE_RATE)


class PacketSequence:
    """Creates packets in a sequence for exercising stream worker behavior.

    A test can create a PacketSequence(N) that will raise a StopIteration after
    N packets.  Each packet has an arbitrary monotomically increasing dts/pts value
    that is parseable by the worker, but a test can manipulate the values to
    exercise corner cases.
    """

    def __init__(self, num_packets):
        """Initialize the sequence with the number of packets it provides."""
        self.packet = 0
        self.num_packets = num_packets

    def __iter__(self):
        """Reset the sequence."""
        self.packet = 0
        return self

    def __next__(self):
        """Return the next packet."""
        if self.packet >= self.num_packets:
            raise StopIteration
        self.packet += 1

        class FakePacket(bytearray):
            # Be a bytearray so that memoryview works
            def __init__(self):
                super().__init__(3)

            time_base = fractions.Fraction(1, VIDEO_FRAME_RATE)
            dts = int(self.packet * PACKET_DURATION / time_base)
            pts = int(self.packet * PACKET_DURATION / time_base)
            duration = int(PACKET_DURATION / time_base)
            stream = VIDEO_STREAM
            # Pretend we get 1 keyframe every second
            is_keyframe = not (self.packet - 1) % (VIDEO_FRAME_RATE * KEYFRAME_INTERVAL)
            size = 3

        return FakePacket()


class FakePyAvContainer:
    """A fake container returned by mock av.open for a stream."""

    def __init__(self, video_stream, audio_stream):
        """Initialize the fake container."""
        # Tests can override this to trigger different worker behavior
        self.packets = PacketSequence(0)

        class FakePyAvStreams:
            video = [video_stream] if video_stream else []
            audio = [audio_stream] if audio_stream else []

        self.streams = FakePyAvStreams()

        class FakePyAvFormat:
            name = "ignored-format"

        self.format = FakePyAvFormat()

    def demux(self, streams):
        """Decode the streams from container, and return a packet sequence."""
        return self.packets

    def close(self):
        """Close the container."""
        return


class FakePyAvBuffer:
    """Holds outputs of the decoded stream for tests to assert on results."""

    def __init__(self):
        """Initialize the FakePyAvBuffer."""
        self.segments = []
        self.audio_packets = []
        self.video_packets = []

    def add_stream(self, template=None):
        """Create an output buffer that captures packets for test to examine."""

        class FakeStream:
            def __init__(self, capture_packets):
                self.capture_packets = capture_packets

            def close(self):
                return

            def mux(self, packet):
                self.capture_packets.append(packet)

        if template.name == AUDIO_STREAM_FORMAT:
            return FakeStream(self.audio_packets)
        return FakeStream(self.video_packets)

    def mux(self, packet):
        """Capture a packet for tests to examine."""
        # Forward to appropriate FakeStream
        packet.stream.mux(packet)

    def close(self):
        """Close the buffer."""
        return

    def capture_output_segment(self, segment):
        """Capture the output segment for tests to inspect."""
        self.segments.append(segment)

    @property
    def complete_segments(self):
        """Return only the complete segments."""
        return [segment for segment in self.segments if segment.complete]


class MockPyAv:
    """Mocks out av.open."""

    def __init__(self, video=True, audio=False):
        """Initialize the MockPyAv."""
        video_stream = VIDEO_STREAM if video else None
        audio_stream = AUDIO_STREAM if audio else None
        self.container = FakePyAvContainer(
            video_stream=video_stream, audio_stream=audio_stream
        )
        self.capture_buffer = FakePyAvBuffer()

    def open(self, stream_source, *args, **kwargs):
        """Return a stream or buffer depending on args."""
        if isinstance(stream_source, io.BytesIO):
            return self.capture_buffer
        return self.container


class MockFlushPart:
    """Class to hold a wrapper function for check_flush_part."""

    # Wrap this method with a preceding write so the BytesIO pointer moves
    check_flush_part = SegmentBuffer.check_flush_part

    @classmethod
    def wrapped_check_flush_part(cls, segment_buffer, packet):
        """Wrap check_flush_part to also advance the memory_file pointer."""
        segment_buffer._memory_file.write(b"0")
        return cls.check_flush_part(segment_buffer, packet)


async def async_decode_stream(hass, packets, py_av=None):
    """Start a stream worker that decodes incoming stream packets into output segments."""
    stream = Stream(hass, STREAM_SOURCE, {})
    stream.add_provider(HLS_PROVIDER)

    if not py_av:
        py_av = MockPyAv()
    py_av.container.packets = packets

    with patch("av.open", new=py_av.open), patch(
        "homeassistant.components.stream.core.StreamOutput.put",
        side_effect=py_av.capture_buffer.capture_output_segment,
    ), patch(
        "homeassistant.components.stream.worker.SegmentBuffer.check_flush_part",
        side_effect=MockFlushPart.wrapped_check_flush_part,
        autospec=True,
    ):
        segment_buffer = SegmentBuffer(stream.outputs)
        stream_worker(STREAM_SOURCE, {}, segment_buffer, threading.Event())
        await hass.async_block_till_done()

    return py_av.capture_buffer


async def test_stream_open_fails(hass):
    """Test failure on stream open."""
    stream = Stream(hass, STREAM_SOURCE, {})
    stream.add_provider(HLS_PROVIDER)
    with patch("av.open") as av_open:
        av_open.side_effect = av.error.InvalidDataError(-2, "error")
        segment_buffer = SegmentBuffer(stream.outputs)
        stream_worker(STREAM_SOURCE, {}, segment_buffer, threading.Event())
        await hass.async_block_till_done()
        av_open.assert_called_once()


async def test_stream_worker_success(hass):
    """Test a short stream that ends and outputs everything correctly."""
    decoded_stream = await async_decode_stream(
        hass, PacketSequence(TEST_SEQUENCE_LENGTH)
    )
    segments = decoded_stream.segments
    complete_segments = decoded_stream.complete_segments
    # Check number of segments. A segment is only formed when a packet from the next
    # segment arrives, hence the subtraction of one from the sequence length.
    assert len(complete_segments) == int(
        (TEST_SEQUENCE_LENGTH - 1) * SEGMENTS_PER_PACKET
    )
    # Check sequence numbers
    assert all(segments[i].sequence == i for i in range(len(segments)))
    # Check segment durations
    assert all(s.duration == SEGMENT_DURATION for s in complete_segments)
    assert len(decoded_stream.video_packets) == TEST_SEQUENCE_LENGTH
    assert len(decoded_stream.audio_packets) == 0


async def test_skip_out_of_order_packet(hass):
    """Skip a single out of order packet."""
    packets = list(PacketSequence(TEST_SEQUENCE_LENGTH))
    # for this test, make sure the out of order index doesn't happen on a keyframe
    out_of_order_index = OUT_OF_ORDER_PACKET_INDEX
    if packets[out_of_order_index].is_keyframe:
        out_of_order_index += 1
    # This packet is out of order
    assert not packets[out_of_order_index].is_keyframe
    packets[out_of_order_index].dts = -9090

    decoded_stream = await async_decode_stream(hass, iter(packets))
    segments = decoded_stream.segments
    complete_segments = decoded_stream.complete_segments
    # Check sequence numbers
    assert all(segments[i].sequence == i for i in range(len(segments)))
    # If skipped packet would have been the first packet of a segment, the previous
    # segment will be longer by a packet duration
    # We also may possibly lose a segment due to the shifting pts boundary
    if out_of_order_index % PACKETS_PER_SEGMENT == 0:
        # Check duration of affected segment and remove it
        longer_segment_index = int((out_of_order_index - 1) * SEGMENTS_PER_PACKET)
        assert (
            segments[longer_segment_index].duration
            == SEGMENT_DURATION + PACKET_DURATION
        )
        del segments[longer_segment_index]
        # Check number of segments
        assert len(complete_segments) == int(
            (len(packets) - 1 - 1) * SEGMENTS_PER_PACKET - 1
        )
    else:  # Otherwise segment durations and number of segments are unaffected
        # Check number of segments
        assert len(complete_segments) == int((len(packets) - 1) * SEGMENTS_PER_PACKET)
    # Check remaining segment durations
    assert all(s.duration == SEGMENT_DURATION for s in complete_segments)
    assert len(decoded_stream.video_packets) == len(packets) - 1
    assert len(decoded_stream.audio_packets) == 0


async def test_discard_old_packets(hass):
    """Skip a series of out of order packets."""

    packets = list(PacketSequence(TEST_SEQUENCE_LENGTH))
    # Packets after this one are considered out of order
    packets[OUT_OF_ORDER_PACKET_INDEX - 1].dts = 9090

    decoded_stream = await async_decode_stream(hass, iter(packets))
    segments = decoded_stream.segments
    complete_segments = decoded_stream.complete_segments
    # Check number of segments
    assert len(complete_segments) == int(
        (OUT_OF_ORDER_PACKET_INDEX - 1) * SEGMENTS_PER_PACKET
    )
    # Check sequence numbers
    assert all(segments[i].sequence == i for i in range(len(segments)))
    # Check segment durations
    assert all(s.duration == SEGMENT_DURATION for s in complete_segments)
    assert len(decoded_stream.video_packets) == OUT_OF_ORDER_PACKET_INDEX
    assert len(decoded_stream.audio_packets) == 0


async def test_packet_overflow(hass):
    """Packet is too far out of order, and looks like overflow, ending stream early."""

    packets = list(PacketSequence(TEST_SEQUENCE_LENGTH))
    # Packet is so far out of order, exceeds max gap and looks like overflow
    packets[OUT_OF_ORDER_PACKET_INDEX].dts = -9000000

    decoded_stream = await async_decode_stream(hass, iter(packets))
    segments = decoded_stream.segments
    complete_segments = decoded_stream.complete_segments
    # Check number of segments
    assert len(complete_segments) == int(
        (OUT_OF_ORDER_PACKET_INDEX - 1) * SEGMENTS_PER_PACKET
    )
    # Check sequence numbers
    assert all(segments[i].sequence == i for i in range(len(segments)))
    # Check segment durations
    assert all(s.duration == SEGMENT_DURATION for s in complete_segments)
    assert len(decoded_stream.video_packets) == OUT_OF_ORDER_PACKET_INDEX
    assert len(decoded_stream.audio_packets) == 0


async def test_skip_initial_bad_packets(hass):
    """Tests a small number of initial "bad" packets with missing dts."""

    num_packets = LONGER_TEST_SEQUENCE_LENGTH
    packets = list(PacketSequence(num_packets))
    num_bad_packets = MAX_MISSING_DTS - 1
    for i in range(0, num_bad_packets):
        packets[i].dts = None

    decoded_stream = await async_decode_stream(hass, iter(packets))
    segments = decoded_stream.segments
    complete_segments = decoded_stream.complete_segments
    # Check sequence numbers
    assert all(segments[i].sequence == i for i in range(len(segments)))
    # Check segment durations
    assert all(s.duration == SEGMENT_DURATION for s in complete_segments)
    assert (
        len(decoded_stream.video_packets)
        == num_packets
        - math.ceil(num_bad_packets / (VIDEO_FRAME_RATE * KEYFRAME_INTERVAL))
        * VIDEO_FRAME_RATE
        * KEYFRAME_INTERVAL
    )
    # Check number of segments
    assert len(complete_segments) == int(
        (len(decoded_stream.video_packets) - 1) * SEGMENTS_PER_PACKET
    )
    assert len(decoded_stream.audio_packets) == 0


async def test_too_many_initial_bad_packets_fails(hass):
    """Test initial bad packets are too high, causing it to never start."""

    num_packets = LONGER_TEST_SEQUENCE_LENGTH
    packets = list(PacketSequence(num_packets))
    num_bad_packets = MAX_MISSING_DTS + 1
    for i in range(0, num_bad_packets):
        packets[i].dts = None

    decoded_stream = await async_decode_stream(hass, iter(packets))
    segments = decoded_stream.segments
    assert len(segments) == 0
    assert len(decoded_stream.video_packets) == 0
    assert len(decoded_stream.audio_packets) == 0


async def test_skip_missing_dts(hass):
    """Test packets in the middle of the stream missing DTS are skipped."""

    num_packets = LONGER_TEST_SEQUENCE_LENGTH
    packets = list(PacketSequence(num_packets))
    bad_packet_start = int(LONGER_TEST_SEQUENCE_LENGTH / 2)
    num_bad_packets = MAX_MISSING_DTS - 1
    for i in range(bad_packet_start, bad_packet_start + num_bad_packets):
        if packets[i].is_keyframe:
            num_bad_packets -= 1
            continue
        packets[i].dts = None

    decoded_stream = await async_decode_stream(hass, iter(packets))
    segments = decoded_stream.segments
    complete_segments = decoded_stream.complete_segments
    # Check sequence numbers
    assert all(segments[i].sequence == i for i in range(len(segments)))
    # Check segment durations (not counting the last segment)
    assert sum(segment.duration for segment in complete_segments) >= len(segments) - 1
    assert len(decoded_stream.video_packets) == num_packets - num_bad_packets
    assert len(decoded_stream.audio_packets) == 0


async def test_too_many_bad_packets(hass):
    """Test bad packets are too many, causing it to end."""

    num_packets = LONGER_TEST_SEQUENCE_LENGTH
    packets = list(PacketSequence(num_packets))
    bad_packet_start = int(LONGER_TEST_SEQUENCE_LENGTH / 2)
    num_bad_packets = MAX_MISSING_DTS + 1
    for i in range(bad_packet_start, bad_packet_start + num_bad_packets):
        packets[i].dts = None

    decoded_stream = await async_decode_stream(hass, iter(packets))
    complete_segments = decoded_stream.complete_segments
    assert len(complete_segments) == int((bad_packet_start - 1) * SEGMENTS_PER_PACKET)
    assert len(decoded_stream.video_packets) == bad_packet_start
    assert len(decoded_stream.audio_packets) == 0


async def test_no_video_stream(hass):
    """Test no video stream in the container means no resulting output."""
    py_av = MockPyAv(video=False)

    decoded_stream = await async_decode_stream(
        hass, PacketSequence(TEST_SEQUENCE_LENGTH), py_av=py_av
    )
    # Note: This failure scenario does not output an end of stream
    segments = decoded_stream.segments
    assert len(segments) == 0
    assert len(decoded_stream.video_packets) == 0
    assert len(decoded_stream.audio_packets) == 0


async def test_audio_packets_not_found(hass):
    """Set up an audio stream, but no audio packets are found."""
    py_av = MockPyAv(audio=True)

    num_packets = PACKETS_TO_WAIT_FOR_AUDIO + 1
    packets = PacketSequence(num_packets)  # Contains only video packets

    decoded_stream = await async_decode_stream(hass, iter(packets), py_av=py_av)
    complete_segments = decoded_stream.complete_segments
    assert len(complete_segments) == int((num_packets - 1) * SEGMENTS_PER_PACKET)
    assert len(decoded_stream.video_packets) == num_packets
    assert len(decoded_stream.audio_packets) == 0


async def test_adts_aac_audio(hass):
    """Set up an ADTS AAC audio stream and disable audio."""
    py_av = MockPyAv(audio=True)

    num_packets = PACKETS_TO_WAIT_FOR_AUDIO + 1
    packets = list(PacketSequence(num_packets))
    packets[1].stream = AUDIO_STREAM
    packets[1].dts = int(packets[0].dts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)
    packets[1].pts = int(packets[0].pts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)
    # The following is packet data is a sign of ADTS AAC
    packets[1][0] = 255
    packets[1][1] = 241

    decoded_stream = await async_decode_stream(hass, iter(packets), py_av=py_av)
    assert len(decoded_stream.audio_packets) == 0


async def test_audio_is_first_packet(hass):
    """Set up an audio stream and audio packet is the first packet in the stream."""
    py_av = MockPyAv(audio=True)

    num_packets = PACKETS_TO_WAIT_FOR_AUDIO + 1
    packets = list(PacketSequence(num_packets))
    # Pair up an audio packet for each video packet
    packets[0].stream = AUDIO_STREAM
    packets[0].dts = int(packets[1].dts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)
    packets[0].pts = int(packets[1].pts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)
    packets[1].is_keyframe = True  # Move the video keyframe from packet 0 to packet 1
    packets[2].stream = AUDIO_STREAM
    packets[2].dts = int(packets[3].dts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)
    packets[2].pts = int(packets[3].pts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)

    decoded_stream = await async_decode_stream(hass, iter(packets), py_av=py_av)
    complete_segments = decoded_stream.complete_segments
    # The audio packets are segmented with the video packets
    assert len(complete_segments) == int((num_packets - 2 - 1) * SEGMENTS_PER_PACKET)
    assert len(decoded_stream.video_packets) == num_packets - 2
    assert len(decoded_stream.audio_packets) == 1


async def test_audio_packets_found(hass):
    """Set up an audio stream and audio packets are found at the start of the stream."""
    py_av = MockPyAv(audio=True)

    num_packets = PACKETS_TO_WAIT_FOR_AUDIO + 1
    packets = list(PacketSequence(num_packets))
    packets[1].stream = AUDIO_STREAM
    packets[1].dts = int(packets[0].dts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)
    packets[1].pts = int(packets[0].pts / VIDEO_FRAME_RATE * AUDIO_SAMPLE_RATE)

    decoded_stream = await async_decode_stream(hass, iter(packets), py_av=py_av)
    complete_segments = decoded_stream.complete_segments
    # The audio packet above is buffered with the video packet
    assert len(complete_segments) == int((num_packets - 1 - 1) * SEGMENTS_PER_PACKET)
    assert len(decoded_stream.video_packets) == num_packets - 1
    assert len(decoded_stream.audio_packets) == 1


async def test_pts_out_of_order(hass):
    """Test pts can be out of order and still be valid."""

    # Create a sequence of packets with some out of order pts
    packets = list(PacketSequence(TEST_SEQUENCE_LENGTH))
    for i, _ in enumerate(packets):
        if i % PACKETS_PER_SEGMENT == 1:
            packets[i].pts = packets[i - 1].pts - 1
            packets[i].is_keyframe = False

    decoded_stream = await async_decode_stream(hass, iter(packets))
    segments = decoded_stream.segments
    complete_segments = decoded_stream.complete_segments
    # Check number of segments
    assert len(complete_segments) == int(
        (TEST_SEQUENCE_LENGTH - 1) * SEGMENTS_PER_PACKET
    )
    # Check sequence numbers
    assert all(segments[i].sequence == i for i in range(len(segments)))
    # Check segment durations
    assert all(s.duration == SEGMENT_DURATION for s in complete_segments)
    assert len(decoded_stream.video_packets) == len(packets)
    assert len(decoded_stream.audio_packets) == 0


async def test_stream_stopped_while_decoding(hass):
    """Tests that worker quits when stop() is called while decodign."""
    # Add some synchronization so that the test can pause the background
    # worker. When the worker is stopped, the test invokes stop() which
    # will cause the worker thread to exit once it enters the decode
    # loop
    worker_open = threading.Event()
    worker_wake = threading.Event()

    stream = Stream(hass, STREAM_SOURCE, {})
    stream.add_provider(HLS_PROVIDER)

    py_av = MockPyAv()
    py_av.container.packets = PacketSequence(TEST_SEQUENCE_LENGTH)

    def blocking_open(stream_source, *args, **kwargs):
        # Let test know the thread is running
        worker_open.set()
        # Block worker thread until test wakes up
        worker_wake.wait()
        return py_av.open(stream_source, args, kwargs)

    with patch("av.open", new=blocking_open):
        stream.start()
        assert worker_open.wait(TIMEOUT)
        # Note: There is a race here where the worker could start as soon
        # as the wake event is sent, completing all decode work.
        worker_wake.set()
        stream.stop()


async def test_update_stream_source(hass):
    """Tests that the worker is re-invoked when the stream source is updated."""
    worker_open = threading.Event()
    worker_wake = threading.Event()

    stream = Stream(hass, STREAM_SOURCE, {})
    stream.add_provider(HLS_PROVIDER)
    # Note that keepalive is not set here.  The stream is "restarted" even though
    # it is not stopping due to failure.

    py_av = MockPyAv()
    py_av.container.packets = PacketSequence(TEST_SEQUENCE_LENGTH)

    last_stream_source = None

    def blocking_open(stream_source, *args, **kwargs):
        nonlocal last_stream_source
        if not isinstance(stream_source, io.BytesIO):
            last_stream_source = stream_source
        # Let test know the thread is running
        worker_open.set()
        # Block worker thread until test wakes up
        worker_wake.wait()
        return py_av.open(stream_source, args, kwargs)

    with patch("av.open", new=blocking_open), patch(
        "homeassistant.components.stream.worker.SegmentBuffer.check_flush_part",
        side_effect=MockFlushPart.wrapped_check_flush_part,
        autospec=True,
    ):
        stream.start()
        assert worker_open.wait(TIMEOUT)
        assert last_stream_source == STREAM_SOURCE

        # Update the stream source, then the test wakes up the worker and assert
        # that it re-opens the new stream (the test again waits on thread_started)
        worker_open.clear()
        stream.update_source(STREAM_SOURCE + "-updated-source")
        worker_wake.set()
        assert worker_open.wait(TIMEOUT)
        assert last_stream_source == STREAM_SOURCE + "-updated-source"
        worker_wake.set()

        # Cleanup
        stream.stop()


async def test_worker_log(hass, caplog):
    """Test that the worker logs the url without username and password."""
    stream = Stream(hass, "https://abcd:efgh@foo.bar", {})
    stream.add_provider(HLS_PROVIDER)
    with patch("av.open") as av_open:
        av_open.side_effect = av.error.InvalidDataError(-2, "error")
        segment_buffer = SegmentBuffer(stream.outputs)
        stream_worker(
            "https://abcd:efgh@foo.bar", {}, segment_buffer, threading.Event()
        )
        await hass.async_block_till_done()
    assert "https://abcd:efgh@foo.bar" not in caplog.text
    assert "https://****:****@foo.bar" in caplog.text


async def test_durations(hass, record_worker_sync):
    """Test that the duration metadata matches the media."""
    await async_setup_component(hass, "stream", {"stream": {}})

    source = generate_h264_video()
    stream = create_stream(hass, source, {})

    # use record_worker_sync to grab output segments
    with patch.object(hass.config, "is_allowed_path", return_value=True):
        await stream.async_record("/example/path")

    complete_segments = list(await record_worker_sync.get_segments())[:-1]
    assert len(complete_segments) >= 1

    # check that the Part duration metadata matches the durations in the media
    running_metadata_duration = 0
    for segment in complete_segments:
        for part in segment.parts:
            av_part = av.open(io.BytesIO(segment.init + part.data))
            running_metadata_duration += part.duration
            # av_part.duration will just return the largest dts in av_part.
            # When we normalize by av.time_base this should equal the running duration
            assert math.isclose(
                running_metadata_duration,
                av_part.duration / av.time_base,
                abs_tol=1e-6,
            )
            av_part.close()
    # check that the Part durations are consistent with the Segment durations
    for segment in complete_segments:
        assert math.isclose(
            sum(part.duration for part in segment.parts), segment.duration, abs_tol=1e-6
        )

    await record_worker_sync.join()

    stream.stop()


async def test_has_keyframe(hass, record_worker_sync):
    """Test that the has_keyframe metadata matches the media."""
    await async_setup_component(hass, "stream", {"stream": {}})

    source = generate_h264_video()
    stream = create_stream(hass, source, {})

    # use record_worker_sync to grab output segments
    with patch.object(hass.config, "is_allowed_path", return_value=True):
        await stream.async_record("/example/path")

    # Our test video has keyframes every second. Use smaller parts so we have more
    # part boundaries to better test keyframe logic.
    with patch("homeassistant.components.stream.worker.TARGET_PART_DURATION", 0.25):
        complete_segments = list(await record_worker_sync.get_segments())[:-1]
    assert len(complete_segments) >= 1

    # check that the Part has_keyframe metadata matches the keyframes in the media
    for segment in complete_segments:
        for part in segment.parts:
            av_part = av.open(io.BytesIO(segment.init + part.data))
            media_has_keyframe = any(
                packet.is_keyframe for packet in av_part.demux(av_part.streams.video[0])
            )
            av_part.close()
            assert part.has_keyframe == media_has_keyframe

    await record_worker_sync.join()

    stream.stop()
