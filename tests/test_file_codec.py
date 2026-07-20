import hashlib
import random

import pytest

from dna_trace_reconstruction.file_codec import (
    DEFAULT_MAX_OLIGO_BASES,
    MAX_FILE_BYTES,
    FileCodecError,
    IntegrityError,
    MissingOligoError,
    OligoFormatError,
    bytes_to_constrained_dna,
    bytes_to_dna,
    constrained_dna_to_bytes,
    decode_file_from_constrained_dna,
    decode_file_from_dna,
    decode_file_from_oligos,
    dna_to_bytes,
    encode_file_to_constrained_dna,
    encode_file_to_dna,
    encode_file_to_oligos,
    inspect_oligo,
    reassemble_dna_from_oligos,
    split_dna_into_oligos,
)


def _mutate_base(sequence: str, index: int) -> str:
    replacement = "C" if sequence[index] == "A" else "A"
    return sequence[:index] + replacement + sequence[index + 1 :]


def test_two_bit_mapping_is_known_and_reversible_for_all_byte_values():
    raw = bytes(range(256))

    assert bytes_to_dna(b"\x00\x1b\xe4\xff") == "AAAAACGTTGCATTTT"
    assert dna_to_bytes(bytes_to_dna(raw)) == raw
    assert bytes_to_dna(b"") == ""
    assert dna_to_bytes("") == b""


def test_constraint_preserving_mapping_is_reversible_and_biologically_valid():
    raw = bytes(range(256))
    encoded = bytes_to_constrained_dna(raw)

    assert constrained_dna_to_bytes(encoded) == raw
    assert len(encoded) == 8 * len(raw)
    assert encoded.count("G") + encoded.count("C") == len(encoded) // 2
    assert all(first != second for first, second in zip(encoded, encoded[1:], strict=False))


def test_constrained_file_round_trip_preserves_binary_data_and_metadata():
    data = b"\x00\xffHelixTrace\x10"
    encoded = encode_file_to_constrained_dna(
        data,
        filename="película-🧬.bin",
        media_type="application/octet-stream",
    )

    recovered = decode_file_from_constrained_dna(encoded)

    assert recovered.data == data
    assert recovered.filename == "película-🧬.bin"
    assert recovered.media_type == "application/octet-stream"
    assert recovered.sha256 == hashlib.sha256(data).hexdigest()


def test_constrained_decoder_rejects_invalid_state_transition():
    encoded = bytes_to_constrained_dna(b"test")
    invalid = encoded[:2] + encoded[1] + encoded[3:]

    with pytest.raises(ValueError, match="invalid constrained codeword"):
        constrained_dna_to_bytes(invalid)


@pytest.mark.parametrize("sequence", ["ACG", "ACGN", "acgt"])
def test_dna_to_bytes_rejects_unaligned_or_noncanonical_dna(sequence):
    with pytest.raises(ValueError):
        dna_to_bytes(sequence)


def test_file_round_trip_preserves_binary_data_and_unicode_metadata():
    data = b"\x00\xff\x10HelixTrace\x00"
    dna = encode_file_to_dna(
        data,
        filename="película-🧬.bin",
        media_type="application/octet-stream",
    )

    recovered = decode_file_from_dna(dna)

    assert recovered.data == data
    assert recovered.filename == "película-🧬.bin"
    assert recovered.media_type == "application/octet-stream"
    assert recovered.sha256 == hashlib.sha256(data).hexdigest()
    assert recovered.size_bytes == len(data)
    assert recovered.version == 1


@pytest.mark.parametrize(
    ("data", "filename", "media_type"),
    [
        (b"", None, None),
        (b"", "", ""),
        (b"hello", "hello.txt", "text/plain"),
    ],
)
def test_file_round_trip_supports_empty_bytes_and_optional_metadata(
    data,
    filename,
    media_type,
):
    recovered = decode_file_from_dna(
        encode_file_to_dna(data, filename=filename, media_type=media_type)
    )

    assert recovered.data == data
    assert recovered.filename == filename
    assert recovered.media_type == media_type


def test_file_frame_detects_single_base_corruption():
    encoded = encode_file_to_dna(b"integrity matters", filename="proof.txt")
    corrupted = _mutate_base(encoded, len(encoded) - 132)

    with pytest.raises(IntegrityError, match="integrity check failed"):
        decode_file_from_dna(corrupted)


def test_file_decoder_reports_truncation_and_trailing_data():
    encoded = encode_file_to_dna(b"hello")

    with pytest.raises(FileCodecError, match="length mismatch"):
        decode_file_from_dna(encoded[:-4])
    with pytest.raises(FileCodecError, match="length mismatch"):
        decode_file_from_dna(encoded + "AAAA")


def test_codec_enforces_explicit_file_and_metadata_limits():
    with pytest.raises(ValueError, match="codec limit"):
        encode_file_to_dna(b"x" * (MAX_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="1024-byte"):
        encode_file_to_dna(b"x", filename="ñ" * 513)
    with pytest.raises(ValueError, match="NUL"):
        encode_file_to_dna(b"x", filename="unsafe\x00name")


def test_oligos_are_bounded_indexed_and_reassemble_in_any_order():
    data = bytes(range(256)) * 2
    framed_dna = encode_file_to_dna(data, filename="sample.bin")
    oligos = list(split_dna_into_oligos(framed_dna))

    assert len(oligos) > 1
    assert all(len(oligo) <= DEFAULT_MAX_OLIGO_BASES for oligo in oligos)
    infos = [inspect_oligo(oligo) for oligo in oligos]
    assert [info.index for info in infos] == list(range(len(oligos)))
    assert {info.total for info in infos} == {len(oligos)}
    assert len({info.file_id for info in infos}) == 1

    random.Random(42).shuffle(oligos)

    assert reassemble_dna_from_oligos(oligos) == framed_dna
    assert decode_file_from_oligos(oligos).data == data


def test_end_to_end_oligo_round_trip_handles_empty_file_and_unicode_name():
    oligos = encode_file_to_oligos(
        b"",
        filename="vacío-🧬.dat",
        media_type="application/octet-stream",
    )

    recovered = decode_file_from_oligos(reversed(oligos))

    assert recovered.data == b""
    assert recovered.filename == "vacío-🧬.dat"
    assert recovered.media_type == "application/octet-stream"


def test_reassembly_reports_missing_oligo_indices():
    oligos = encode_file_to_oligos(b"x" * 300)

    with pytest.raises(MissingOligoError, match=r"missing 1 .* indices: 1"):
        decode_file_from_oligos(oligos[:1] + oligos[2:])


def test_reassembly_rejects_duplicate_and_mixed_file_oligos():
    first = encode_file_to_oligos(b"a" * 100)
    second = encode_file_to_oligos(b"b" * 100)

    with pytest.raises(OligoFormatError, match="duplicate oligo index"):
        decode_file_from_oligos(first + (first[0],))
    with pytest.raises(OligoFormatError, match="different encoded files"):
        decode_file_from_oligos((first[0], second[1], *first[2:]))


def test_oligo_detects_single_base_corruption():
    oligos = list(encode_file_to_oligos(b"error detection" * 20))
    oligos[1] = _mutate_base(oligos[1], len(oligos[1]) - 1)

    with pytest.raises(IntegrityError, match=r"oligos\[1\] integrity check failed"):
        decode_file_from_oligos(oligos)


@pytest.mark.parametrize("max_bases", [0, 123, 125, 262_264])
def test_oligo_size_limit_validation_is_clear(max_bases):
    with pytest.raises((ValueError, TypeError), match="max_oligo_bases"):
        encode_file_to_oligos(b"x", max_oligo_bases=max_bases)


def test_oligo_collection_input_errors_are_readable():
    with pytest.raises(MissingOligoError, match="at least one"):
        decode_file_from_oligos([])
    with pytest.raises(TypeError, match="iterable"):
        decode_file_from_oligos("ACGT")
