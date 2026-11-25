// news-image-20261124 v2 "The World in One Day" — entrypoint.
// Renders entry.png (1024x1024, <=1 MiB) with Python + PIL, or falls back
// to the bundled entry.png when Python/PIL is unavailable.
// Node 22 stdlib only. Never deletes the output directory.
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = process.env.OUTPUT_DIR ?? process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
const OUT = join(OUT_DIR, "entry.png");
const GEN = join(HERE, "generate.py");
const BUNDLED = join(HERE, "entry.png");

function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

function checkPng(path) {
  const buf = readFileSync(path);
  if (buf.length < 33) throw new Error("PNG too small: " + buf.length + " bytes");
  const sig = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (!buf.subarray(0, 8).equals(sig)) throw new Error("bad PNG signature");
  if (buf.toString("latin1", 12, 16) !== "IHDR") throw new Error("missing IHDR");
  const w = buf.readUInt32BE(16);
  const h = buf.readUInt32BE(20);
  if (w !== 1024 || h !== 1024) throw new Error(`bad size ${w}x${h}, want 1024x1024`);
  if (buf.length > 1024 * 1024) throw new Error(`PNG too big: ${buf.length} bytes`);
  // IEND trailer must be intact: last 12 bytes are length 0, "IEND", CRC.
  const tail = buf.subarray(buf.length - 12);
  if (tail.readUInt32BE(0) !== 0 || tail.toString("latin1", 4, 8) !== "IEND") {
    throw new Error("truncated PNG: missing IEND trailer");
  }
  const iendCrc = tail.readUInt32BE(8);
  const expectCrc = 0xae426082; // CRC32 of "IEND"
  if (iendCrc !== expectCrc) throw new Error("corrupt PNG: bad IEND CRC");
  return { bytes: buf.length, sha256: sha256(buf) };
}

function tryPython() {
  for (const py of ["python3", "python"]) {
    const r = spawnSync(py, [GEN], {
      env: { ...process.env, OUTPUT_DIR: OUT_DIR },
      encoding: "utf8",
    });
    if (r.error) continue;
    if (r.status === 0 && existsSync(OUT)) {
      if (r.stdout.trim()) process.stdout.write(r.stdout);
      return true;
    }
    if (r.stderr.trim()) process.stderr.write(r.stderr);
  }
  return false;
}

mkdirSync(OUT_DIR, { recursive: true });

let rendered = false;
if (existsSync(GEN)) rendered = tryPython();
if (!rendered) {
  if (!existsSync(BUNDLED)) {
    throw new Error("no Python/PIL render and no bundled entry.png");
  }
  copyFileSync(BUNDLED, OUT);
  console.log("FALLBACK bundled entry.png");
}

const info = checkPng(OUT);
console.log(`OK ${OUT} ${info.bytes} bytes sha256=${info.sha256}`);
