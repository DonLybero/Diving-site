// Byte-level helpers shared by the parser registry and parsers.

/** Decode file bytes to text: honours UTF-16 BOMs, strips a UTF-8 BOM. */
export function decodeText(bytes) {
  if (bytes.length >= 2) {
    if (bytes[0] === 0xff && bytes[1] === 0xfe) return new TextDecoder('utf-16le').decode(bytes.subarray(2));
    if (bytes[0] === 0xfe && bytes[1] === 0xff) return new TextDecoder('utf-16be').decode(bytes.subarray(2));
  }
  let text = new TextDecoder('utf-8').decode(bytes);
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  return text;
}

/** True when the head of the file contains NUL bytes (i.e. not a text format). */
export function looksBinary(bytes) {
  // UTF-16 text is full of NULs but declares itself with a BOM
  if (bytes.length >= 2 && ((bytes[0] === 0xff && bytes[1] === 0xfe) || (bytes[0] === 0xfe && bytes[1] === 0xff))) return false;
  const n = Math.min(bytes.length, 1024);
  for (let i = 0; i < n; i++) if (bytes[i] === 0) return true;
  return false;
}

/** ASCII check of a byte range against a string, e.g. magic numbers. */
export function bytesMatch(bytes, offset, ascii) {
  if (bytes.length < offset + ascii.length) return false;
  for (let i = 0; i < ascii.length; i++) if (bytes[offset + i] !== ascii.charCodeAt(i)) return false;
  return true;
}
