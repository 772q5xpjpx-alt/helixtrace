"""Deterministic file framing and oligo packaging for synthetic DNA storage.

The codec deliberately separates *digital framing* from biological sequence
design.  It maps two bits to each DNA base, adds versioned metadata and strong
integrity checks, and packages the resulting bytes into self-indexing oligos.
It does not add error-correcting codes, primers, address balancing, or
biochemical constraints; those are separate layers in a production system.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import struct
from collections.abc import Iterable
from dataclasses import dataclass

DNA_ALPHABET = "ACGT"
FORMAT_VERSION = 1
DEFAULT_MAX_OLIGO_BASES = 300
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_FILENAME_BYTES = 1024
MAX_MEDIA_TYPE_BYTES = 255
MAX_OLIGOS = 100_000

_FILE_MAGIC = b"HLXF"
_OLIGO_MAGIC = b"HX"
_FLAG_FILENAME = 0b0000_0001
_FLAG_MEDIA_TYPE = 0b0000_0010
_KNOWN_FILE_FLAGS = _FLAG_FILENAME | _FLAG_MEDIA_TYPE
_FILE_HEADER = struct.Struct(">4sBBHHQ32s")
_FRAME_DIGEST_BYTES = hashlib.sha256().digest_size

# magic, version, flags, file id, zero-based index, total, chunk length
_OLIGO_HEADER = struct.Struct(">2sBB8sIIH")
_OLIGO_TAG_BYTES = 8
_OLIGO_OVERHEAD_BYTES = _OLIGO_HEADER.size + _OLIGO_TAG_BYTES
_MAX_CHUNK_BYTES = (1 << 16) - 1
_MAX_UINT32 = (1 << 32) - 1

_BYTE_TO_DNA = tuple(
    "".join(DNA_ALPHABET[(value >> shift) & 0b11] for shift in (6, 4, 2, 0)) for value in range(256)
)
_DNA_TO_BITS = {base: value for value, base in enumerate(DNA_ALPHABET)}

# Four state-dependent codewords carry one two-bit symbol. Every codeword has
# exactly one GC base and one AT base, and its first base differs from the
# previous emitted base. The resulting stream is exactly 50% GC and has no
# repeated adjacent bases. This deliberately trades density (1 bit/nt) for a
# simple, guaranteed synthesis profile.
_BALANCED_PAIRS = tuple(
    first + second
    for first in DNA_ALPHABET
    for second in DNA_ALPHABET
    if (first in "GC") != (second in "GC")
)
_CONSTRAINED_CODEWORDS = {
    previous: tuple(pair for pair in _BALANCED_PAIRS if pair[0] != previous)[:4]
    for previous in DNA_ALPHABET
}
_CONSTRAINED_REVERSE = {
    previous: {pair: value for value, pair in enumerate(codewords)}
    for previous, codewords in _CONSTRAINED_CODEWORDS.items()
}
_CONSTRAINED_INITIAL_BASE = "A"


class FileCodecError(ValueError):
    """Base exception for malformed or unsupported encoded-file data."""


class IntegrityError(FileCodecError):
    """Raised when a cryptographic digest or oligo tag does not match."""


class OligoFormatError(FileCodecError):
    """Raised when an oligo header or a collection of oligos is inconsistent."""


class MissingOligoError(OligoFormatError):
    """Raised when one or more indexed oligos are absent from a collection."""


@dataclass(frozen=True)
class DecodedFile:
    """One verified file recovered from DNA."""

    data: bytes
    filename: str | None
    media_type: str | None
    sha256: str
    version: int

    @property
    def size_bytes(self) -> int:
        """Return the recovered payload size."""
        return len(self.data)


@dataclass(frozen=True)
class OligoInfo:
    """Verified routing metadata for one encoded oligo."""

    file_id: str
    index: int
    total: int
    payload_bytes: int
    sequence_bases: int
    version: int


@dataclass(frozen=True)
class _OligoRecord:
    file_id: bytes
    index: int
    total: int
    payload: bytes
    sequence_bases: int


def _coerce_bytes(data: bytes | bytearray | memoryview, *, name: str) -> bytes:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"{name} must be bytes-like")
    return bytes(data)


def _validate_limit(name: str, value: int, *, minimum: int = 1) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _validated_dna(sequence: str, *, name: str, allow_empty: bool = True) -> str:
    if not isinstance(sequence, str):
        raise TypeError(f"{name} must be a DNA string")
    if not allow_empty and not sequence:
        raise ValueError(f"{name} cannot be empty")
    invalid_bases = sorted(set(sequence) - set(DNA_ALPHABET))
    if invalid_bases:
        raise ValueError(f"{name} contains invalid DNA bases: {invalid_bases}")
    if len(sequence) % 4:
        raise ValueError(f"{name} length must be divisible by 4 bases")
    return sequence


def bytes_to_dna(data: bytes | bytearray | memoryview) -> str:
    """Map bytes to DNA using ``A=00, C=01, G=10, T=11``.

    The mapping is exact and deterministic.  It is a digital representation,
    not a constrained biological encoder, so it may produce GC imbalance or
    long homopolymers.
    """
    raw = _coerce_bytes(data, name="data")
    return "".join(_BYTE_TO_DNA[value] for value in raw)


def dna_to_bytes(sequence: str) -> bytes:
    """Invert :func:`bytes_to_dna` for a four-base-aligned DNA sequence."""
    sequence = _validated_dna(sequence, name="sequence")
    output = bytearray(len(sequence) // 4)
    for byte_index, offset in enumerate(range(0, len(sequence), 4)):
        value = 0
        for base in sequence[offset : offset + 4]:
            value = (value << 2) | _DNA_TO_BITS[base]
        output[byte_index] = value
    return bytes(output)


def bytes_to_constrained_dna(data: bytes | bytearray | memoryview) -> str:
    """Encode bytes at one bit/base with guaranteed GC balance and no runs.

    Each two-bit input symbol becomes a state-dependent two-base codeword.
    Every pair contains one GC base and one AT base, while its first base is
    chosen to differ from the previously emitted base. Therefore every output
    has exactly 50% GC content and maximum homopolymer length one.
    """
    raw = _coerce_bytes(data, name="data")
    previous = _CONSTRAINED_INITIAL_BASE
    output: list[str] = []
    for byte in raw:
        for shift in (6, 4, 2, 0):
            value = (byte >> shift) & 0b11
            codeword = _CONSTRAINED_CODEWORDS[previous][value]
            output.append(codeword)
            previous = codeword[-1]
    return "".join(output)


def constrained_dna_to_bytes(sequence: str) -> bytes:
    """Invert :func:`bytes_to_constrained_dna` and validate every codeword."""
    if not isinstance(sequence, str):
        raise TypeError("sequence must be a DNA string")
    invalid_bases = sorted(set(sequence) - set(DNA_ALPHABET))
    if invalid_bases:
        raise ValueError(f"sequence contains invalid DNA bases: {invalid_bases}")
    if len(sequence) % 8:
        raise ValueError("constrained DNA length must be divisible by 8 bases")

    previous = _CONSTRAINED_INITIAL_BASE
    output = bytearray()
    byte_value = 0
    pair_count = 0
    for offset in range(0, len(sequence), 2):
        codeword = sequence[offset : offset + 2]
        try:
            value = _CONSTRAINED_REVERSE[previous][codeword]
        except KeyError as error:
            raise ValueError(
                f"invalid constrained codeword {codeword!r} at bases {offset}-{offset + 1}"
            ) from error
        byte_value = (byte_value << 2) | value
        pair_count += 1
        previous = codeword[-1]
        if pair_count == 4:
            output.append(byte_value)
            byte_value = 0
            pair_count = 0
    return bytes(output)


def _encode_metadata(value: str | None, *, name: str, maximum_bytes: int) -> bytes:
    if value is None:
        return b""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")
    if "\x00" in value:
        raise ValueError(f"{name} cannot contain a NUL character")
    encoded = value.encode("utf-8")
    if len(encoded) > maximum_bytes:
        raise ValueError(f"{name} exceeds the {maximum_bytes}-byte UTF-8 limit")
    return encoded


def _frame_file(
    data: bytes | bytearray | memoryview,
    *,
    filename: str | None,
    media_type: str | None,
) -> bytes:
    payload = _coerce_bytes(data, name="data")
    if len(payload) > MAX_FILE_BYTES:
        raise ValueError(f"data exceeds the {MAX_FILE_BYTES}-byte codec limit")

    encoded_filename = _encode_metadata(
        filename,
        name="filename",
        maximum_bytes=MAX_FILENAME_BYTES,
    )
    encoded_media_type = _encode_metadata(
        media_type,
        name="media_type",
        maximum_bytes=MAX_MEDIA_TYPE_BYTES,
    )

    flags = 0
    if filename is not None:
        flags |= _FLAG_FILENAME
    if media_type is not None:
        flags |= _FLAG_MEDIA_TYPE

    payload_digest = hashlib.sha256(payload).digest()
    header = _FILE_HEADER.pack(
        _FILE_MAGIC,
        FORMAT_VERSION,
        flags,
        len(encoded_filename),
        len(encoded_media_type),
        len(payload),
        payload_digest,
    )
    integrity_data = header + encoded_filename + encoded_media_type + payload
    return integrity_data + hashlib.sha256(integrity_data).digest()


def _decode_frame(frame: bytes) -> DecodedFile:
    minimum_length = _FILE_HEADER.size + _FRAME_DIGEST_BYTES
    if len(frame) < minimum_length:
        raise FileCodecError(f"encoded file is truncated: expected at least {minimum_length} bytes")

    try:
        (
            magic,
            version,
            flags,
            filename_length,
            media_type_length,
            payload_length,
            expected_payload_digest,
        ) = _FILE_HEADER.unpack_from(frame)
    except struct.error as error:  # pragma: no cover - guarded by the length check
        raise FileCodecError("encoded file has an unreadable header") from error

    if magic != _FILE_MAGIC:
        raise FileCodecError("encoded file magic does not match HelixTrace format")
    if version != FORMAT_VERSION:
        raise FileCodecError(
            f"unsupported file format version {version}; expected {FORMAT_VERSION}"
        )
    if flags & ~_KNOWN_FILE_FLAGS:
        raise FileCodecError(f"encoded file uses unsupported flags 0x{flags:02x}")
    if not flags & _FLAG_FILENAME and filename_length:
        raise FileCodecError("filename flag and length are inconsistent")
    if not flags & _FLAG_MEDIA_TYPE and media_type_length:
        raise FileCodecError("media-type flag and length are inconsistent")
    if filename_length > MAX_FILENAME_BYTES:
        raise FileCodecError(f"encoded filename exceeds the {MAX_FILENAME_BYTES}-byte UTF-8 limit")
    if media_type_length > MAX_MEDIA_TYPE_BYTES:
        raise FileCodecError(
            f"encoded media type exceeds the {MAX_MEDIA_TYPE_BYTES}-byte UTF-8 limit"
        )
    if payload_length > MAX_FILE_BYTES:
        raise FileCodecError(f"encoded payload exceeds the {MAX_FILE_BYTES}-byte codec limit")

    expected_length = (
        _FILE_HEADER.size
        + filename_length
        + media_type_length
        + payload_length
        + _FRAME_DIGEST_BYTES
    )
    if len(frame) != expected_length:
        raise FileCodecError(
            f"encoded file length mismatch: header declares {expected_length} bytes, "
            f"received {len(frame)}"
        )

    integrity_data = frame[:-_FRAME_DIGEST_BYTES]
    actual_frame_digest = hashlib.sha256(integrity_data).digest()
    if not hmac.compare_digest(actual_frame_digest, frame[-_FRAME_DIGEST_BYTES:]):
        raise IntegrityError("encoded file integrity check failed")

    metadata_offset = _FILE_HEADER.size
    filename_end = metadata_offset + filename_length
    media_type_end = filename_end + media_type_length
    payload_end = media_type_end + payload_length

    try:
        filename = (
            frame[metadata_offset:filename_end].decode("utf-8") if flags & _FLAG_FILENAME else None
        )
        media_type = (
            frame[filename_end:media_type_end].decode("utf-8") if flags & _FLAG_MEDIA_TYPE else None
        )
    except UnicodeDecodeError as error:
        raise FileCodecError("encoded file metadata is not valid UTF-8") from error

    payload = frame[media_type_end:payload_end]
    actual_payload_digest = hashlib.sha256(payload).digest()
    if not hmac.compare_digest(actual_payload_digest, expected_payload_digest):
        raise IntegrityError("recovered file SHA-256 does not match the stored digest")

    return DecodedFile(
        data=payload,
        filename=filename,
        media_type=media_type,
        sha256=actual_payload_digest.hex(),
        version=version,
    )


def encode_file_to_dna(
    data: bytes | bytearray | memoryview,
    *,
    filename: str | None = None,
    media_type: str | None = None,
) -> str:
    """Frame one file and return its reversible DNA representation."""
    return bytes_to_dna(_frame_file(data, filename=filename, media_type=media_type))


def decode_file_from_dna(sequence: str) -> DecodedFile:
    """Decode and verify one framed file represented as DNA."""
    try:
        frame = dna_to_bytes(sequence)
    except (TypeError, ValueError) as error:
        raise FileCodecError(str(error)) from error
    return _decode_frame(frame)


def encode_file_to_constrained_dna(
    data: bytes | bytearray | memoryview,
    *,
    filename: str | None = None,
    media_type: str | None = None,
) -> str:
    """Frame a file and encode it with a guaranteed 50%-GC DNA code."""
    return bytes_to_constrained_dna(_frame_file(data, filename=filename, media_type=media_type))


def decode_file_from_constrained_dna(sequence: str) -> DecodedFile:
    """Decode and integrity-check a file produced by the constrained encoder."""
    try:
        frame = constrained_dna_to_bytes(sequence)
    except (TypeError, ValueError) as error:
        raise FileCodecError(str(error)) from error
    return _decode_frame(frame)


def _oligo_payload_capacity(max_oligo_bases: int) -> int:
    _validate_limit("max_oligo_bases", max_oligo_bases)
    if max_oligo_bases % 4:
        raise ValueError("max_oligo_bases must be divisible by 4")
    capacity = max_oligo_bases // 4 - _OLIGO_OVERHEAD_BYTES
    if capacity < 1:
        minimum_bases = (_OLIGO_OVERHEAD_BYTES + 1) * 4
        raise ValueError(
            f"max_oligo_bases must be at least {minimum_bases} to carry one payload byte"
        )
    if capacity > _MAX_CHUNK_BYTES:
        raise ValueError(
            f"max_oligo_bases is too large; per-oligo payload cannot exceed "
            f"{_MAX_CHUNK_BYTES} bytes"
        )
    return capacity


def _build_oligo(
    payload: bytes,
    *,
    file_id: bytes,
    index: int,
    total: int,
) -> str:
    header = _OLIGO_HEADER.pack(
        _OLIGO_MAGIC,
        FORMAT_VERSION,
        0,
        file_id,
        index,
        total,
        len(payload),
    )
    integrity_data = header + payload
    tag = hashlib.sha256(integrity_data).digest()[:_OLIGO_TAG_BYTES]
    return bytes_to_dna(integrity_data + tag)


def split_dna_into_oligos(
    sequence: str,
    *,
    max_oligo_bases: int = DEFAULT_MAX_OLIGO_BASES,
) -> tuple[str, ...]:
    """Package byte-aligned DNA into independently verified indexed oligos.

    The returned sequences may be supplied to reconstruction in any order.
    Their headers restore ordering, but they do not solve read clustering: the
    caller must still group noisy reads by source oligo before reconstruction.
    """
    sequence = _validated_dna(sequence, name="sequence", allow_empty=False)
    framed_bytes = dna_to_bytes(sequence)
    capacity = _oligo_payload_capacity(max_oligo_bases)
    total = math.ceil(len(framed_bytes) / capacity)
    if total > min(MAX_OLIGOS, _MAX_UINT32):
        raise ValueError(
            f"encoded data requires {total} oligos; maximum supported is {MAX_OLIGOS}. "
            "Use a larger max_oligo_bases value."
        )

    file_id = hashlib.sha256(framed_bytes).digest()[:8]
    return tuple(
        _build_oligo(
            framed_bytes[offset : offset + capacity],
            file_id=file_id,
            index=index,
            total=total,
        )
        for index, offset in enumerate(range(0, len(framed_bytes), capacity))
    )


def _parse_oligo(sequence: str, *, position: int | None = None) -> _OligoRecord:
    label = "oligo" if position is None else f"oligos[{position}]"
    try:
        sequence = _validated_dna(sequence, name=label, allow_empty=False)
    except (TypeError, ValueError) as error:
        raise OligoFormatError(str(error)) from error

    raw = dna_to_bytes(sequence)
    if len(raw) < _OLIGO_OVERHEAD_BYTES:
        raise OligoFormatError(
            f"{label} is truncated: expected at least {_OLIGO_OVERHEAD_BYTES} bytes"
        )

    try:
        magic, version, flags, file_id, index, total, payload_length = _OLIGO_HEADER.unpack_from(
            raw
        )
    except struct.error as error:  # pragma: no cover - guarded by the length check
        raise OligoFormatError(f"{label} has an unreadable header") from error

    if magic != _OLIGO_MAGIC:
        raise OligoFormatError(f"{label} magic does not match HelixTrace oligo format")
    if version != FORMAT_VERSION:
        raise OligoFormatError(
            f"{label} uses unsupported version {version}; expected {FORMAT_VERSION}"
        )
    if flags:
        raise OligoFormatError(f"{label} uses unsupported flags 0x{flags:02x}")
    if not 1 <= total <= MAX_OLIGOS:
        raise OligoFormatError(f"{label} declares invalid total oligo count {total}")
    if index >= total:
        raise OligoFormatError(f"{label} index {index} is outside total count {total}")

    expected_length = _OLIGO_HEADER.size + payload_length + _OLIGO_TAG_BYTES
    if len(raw) != expected_length:
        raise OligoFormatError(
            f"{label} length mismatch: header declares {expected_length} bytes, received {len(raw)}"
        )

    integrity_data = raw[:-_OLIGO_TAG_BYTES]
    expected_tag = hashlib.sha256(integrity_data).digest()[:_OLIGO_TAG_BYTES]
    if not hmac.compare_digest(expected_tag, raw[-_OLIGO_TAG_BYTES:]):
        raise IntegrityError(f"{label} integrity check failed")

    return _OligoRecord(
        file_id=file_id,
        index=index,
        total=total,
        payload=raw[_OLIGO_HEADER.size : -_OLIGO_TAG_BYTES],
        sequence_bases=len(sequence),
    )


def inspect_oligo(sequence: str) -> OligoInfo:
    """Validate one oligo and return its routing metadata."""
    record = _parse_oligo(sequence)
    return OligoInfo(
        file_id=record.file_id.hex(),
        index=record.index,
        total=record.total,
        payload_bytes=len(record.payload),
        sequence_bases=record.sequence_bases,
        version=FORMAT_VERSION,
    )


def _reassemble_oligo_bytes(oligos: Iterable[str]) -> bytes:
    if isinstance(oligos, (str, bytes)):
        raise TypeError("oligos must be an iterable of DNA strings, not one string")
    try:
        supplied = tuple(oligos)
    except TypeError as error:
        raise TypeError("oligos must be an iterable of DNA strings") from error
    if not supplied:
        raise MissingOligoError("oligos must contain at least one sequence")

    records = tuple(
        _parse_oligo(sequence, position=index) for index, sequence in enumerate(supplied)
    )
    expected_file_id = records[0].file_id
    expected_total = records[0].total
    by_index: dict[int, bytes] = {}

    for record in records:
        if record.file_id != expected_file_id:
            raise OligoFormatError("oligos belong to different encoded files")
        if record.total != expected_total:
            raise OligoFormatError("oligos declare inconsistent total counts")
        if record.index in by_index:
            raise OligoFormatError(f"duplicate oligo index {record.index}")
        by_index[record.index] = record.payload

    missing = [index for index in range(expected_total) if index not in by_index]
    if missing:
        preview = ", ".join(str(index) for index in missing[:10])
        suffix = " ..." if len(missing) > 10 else ""
        raise MissingOligoError(
            f"missing {len(missing)} of {expected_total} oligos; indices: {preview}{suffix}"
        )

    framed_bytes = b"".join(by_index[index] for index in range(expected_total))
    actual_file_id = hashlib.sha256(framed_bytes).digest()[:8]
    if not hmac.compare_digest(actual_file_id, expected_file_id):
        raise IntegrityError("reassembled oligo set does not match its file identifier")
    return framed_bytes


def reassemble_dna_from_oligos(oligos: Iterable[str]) -> str:
    """Validate, order, and join a complete set of self-indexed oligos."""
    return bytes_to_dna(_reassemble_oligo_bytes(oligos))


def encode_file_to_oligos(
    data: bytes | bytearray | memoryview,
    *,
    filename: str | None = None,
    media_type: str | None = None,
    max_oligo_bases: int = DEFAULT_MAX_OLIGO_BASES,
) -> tuple[str, ...]:
    """Frame one file and split it into self-indexed DNA oligos."""
    sequence = encode_file_to_dna(data, filename=filename, media_type=media_type)
    return split_dna_into_oligos(sequence, max_oligo_bases=max_oligo_bases)


def decode_file_from_oligos(oligos: Iterable[str]) -> DecodedFile:
    """Reassemble, decode, and integrity-check one complete oligo collection."""
    return _decode_frame(_reassemble_oligo_bytes(oligos))
