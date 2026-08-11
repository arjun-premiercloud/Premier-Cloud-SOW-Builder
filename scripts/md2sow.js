// Render a Premier Cloud SOW markdown file as a formatted .docx.
//   node md2sow.js <input.md> <output.docx>
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, ExternalHyperlink, convertInchesToTwip,
} = require('docx');

const [, , IN, OUT] = process.argv;
const md = fs.readFileSync(IN, 'utf8');

const NAVY = '1F3864';
const BLUE = '1155CC';
const GREY = 'F1F3F4';
const RULE = 'D0D5DD';
const AMBER = 'FFF4E5';

const PAGE_W = 12240, MARGIN = 1440;
const USABLE = PAGE_W - MARGIN * 2; // 9360 DXA

// ---------- inline formatting ----------
// Splits on **bold**, *italic* and [text](url); everything else is plain.
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*\n]+\*|\[[^\]]+\]\([^)]+\))/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith('**')) {
      out.push(new TextRun({ text: tok.slice(2, -2), bold: true, ...base }));
    } else if (tok.startsWith('[')) {
      const label = tok.slice(1, tok.indexOf(']'));
      const url = tok.slice(tok.indexOf('(') + 1, -1);
      out.push(new ExternalHyperlink({
        link: url,
        children: [new TextRun({ text: label, style: 'Hyperlink', color: BLUE, underline: {} })],
      }));
    } else {
      out.push(new TextRun({ text: tok.slice(1, -1), italics: true, ...base }));
    }
    last = re.lastIndex;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out.length ? out : [new TextRun({ text: '', ...base })];
}

const stripMd = (s) => s.replace(/\*\*/g, '').replace(/^#+\s*/, '').trim();

// ---------- table ----------
function buildTable(lines) {
  const rows = lines
    .map((l) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim()))
    .filter((cells) => !cells.every((c) => /^-{2,}$/.test(c)));
  if (!rows.length) return null;

  const cols = Math.max(...rows.map((r) => r.length));
  // First column carries labels and runs wider; the rest share what is left.
  const first = cols > 2 ? Math.round(USABLE * 0.28) : Math.round(USABLE * 0.42);
  const rest = Math.floor((USABLE - first) / (cols - 1 || 1));
  const widths = cols === 1 ? [USABLE]
    : [first, ...Array(cols - 1).fill(rest)];
  widths[widths.length - 1] += USABLE - widths.reduce((a, b) => a + b, 0);

  const border = { style: BorderStyle.SINGLE, size: 4, color: RULE };
  const borders = { top: border, bottom: border, left: border, right: border };

  return new Table({
    columnWidths: widths,
    width: { size: USABLE, type: WidthType.DXA },
    rows: rows.map((cells, ri) => new TableRow({
      tableHeader: ri === 0,
      children: Array.from({ length: cols }, (_, ci) => {
        const raw = cells[ci] ?? '';
        const header = ri === 0;
        return new TableCell({
          width: { size: widths[ci], type: WidthType.DXA },
          borders,
          shading: header ? { type: ShadingType.CLEAR, fill: GREY, color: 'auto' } : undefined,
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            spacing: { before: 20, after: 20 },
            children: runs(raw, header ? { bold: true, size: 19 } : { size: 19 }),
          })],
        });
      }),
    })),
  });
}

// ---------- parse ----------
const lines = md.split('\n');
const children = [];
let i = 0;

const heading = (text, level) => {
  const sizes = { 1: 30, 2: 25, 3: 22, 4: 20 };
  return new Paragraph({
    heading: [null, HeadingLevel.HEADING_1, HeadingLevel.HEADING_2,
      HeadingLevel.HEADING_3, HeadingLevel.HEADING_4][level],
    spacing: { before: level === 1 ? 360 : 260, after: 120 },
    keepNext: true,
    border: level === 1
      ? { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 6 } }
      : undefined,
    children: [new TextRun({
      text: stripMd(text), bold: true, size: sizes[level],
      color: level <= 2 ? NAVY : '333333',
    })],
  });
};

while (i < lines.length) {
  const line = lines[i];
  const trimmed = line.trim();

  if (!trimmed) { i++; continue; }

  // table
  if (trimmed.startsWith('|')) {
    const block = [];
    while (i < lines.length && lines[i].trim().startsWith('|')) block.push(lines[i++]);
    const t = buildTable(block);
    if (t) {
      children.push(t);
      children.push(new Paragraph({ spacing: { after: 160 }, children: [new TextRun('')] }));
    }
    continue;
  }

  // horizontal rule
  if (/^-{3,}$/.test(trimmed)) {
    children.push(new Paragraph({
      spacing: { before: 120, after: 120 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 4 } },
      children: [new TextRun('')],
    }));
    i++;
    continue;
  }

  // blockquote -> shaded callout (used for the DRAFT banner)
  if (trimmed.startsWith('>')) {
    const block = [];
    while (i < lines.length && lines[i].trim().startsWith('>')) {
      block.push(lines[i].trim().replace(/^>\s?/, ''));
      i++;
    }
    block.filter((b) => b.trim()).forEach((b, idx, arr) => {
      children.push(new Paragraph({
        spacing: { before: idx === 0 ? 120 : 0, after: idx === arr.length - 1 ? 160 : 40 },
        shading: { type: ShadingType.CLEAR, fill: AMBER, color: 'auto' },
        indent: { left: 200, right: 200 },
        border: { left: { style: BorderStyle.SINGLE, size: 18, color: 'E8A33D', space: 8 } },
        children: runs(b.replace(/^-\s+/, '   •  '), { size: 20 }),
      }));
    });
    continue;
  }

  // heading
  const h = trimmed.match(/^(#{1,4})\s+(.*)$/);
  if (h) { children.push(heading(h[2], h[1].length)); i++; continue; }

  // bullet
  const b = line.match(/^(\s*)-\s+(.*)$/);
  if (b) {
    children.push(new Paragraph({
      numbering: { reference: 'sow-bullets', level: Math.min(Math.floor(b[1].length / 2), 2) },
      spacing: { before: 40, after: 40 },
      children: runs(b[2], { size: 21 }),
    }));
    i++;
    continue;
  }

  // ordered
  const o = line.match(/^(\s*)(\d+)\.\s+(.*)$/);
  if (o) {
    children.push(new Paragraph({
      numbering: { reference: 'sow-numbers', level: Math.min(Math.floor(o[1].length / 3), 2) },
      spacing: { before: 40, after: 40 },
      children: runs(o[3], { size: 21 }),
    }));
    i++;
    continue;
  }

  // paragraph: gather until a blank line or a structural token
  const para = [];
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim() || /^(#{1,4}\s|\||>|-{3,}$)/.test(l.trim()) || /^\s*-\s+/.test(l) || /^\s*\d+\.\s+/.test(l)) break;
    para.push(l.trim());
    i++;
  }
  if (para.length) {
    children.push(new Paragraph({
      spacing: { before: 60, after: 140, line: 276 },
      alignment: AlignmentType.LEFT,
      children: runs(para.join(' '), { size: 21 }),
    }));
  }
}

// ---------- document ----------
const doc = new Document({
  creator: 'Premier Cloud Inc.',
  title: 'Statement of Work',
  styles: {
    default: { document: { run: { font: 'Calibri', size: 21, color: '202124' } } },
  },
  numbering: {
    config: [
      {
        reference: 'sow-bullets',
        levels: [0, 1, 2].map((lvl) => ({
          level: lvl,
          format: LevelFormat.BULLET,
          text: ['•', '◦', '▪'][lvl],
          alignment: AlignmentType.LEFT,
          style: {
            paragraph: {
              indent: {
                left: convertInchesToTwip(0.3 + lvl * 0.28),
                hanging: convertInchesToTwip(0.2),
              },
            },
          },
        })),
      },
      {
        reference: 'sow-numbers',
        levels: [0, 1, 2].map((lvl) => ({
          level: lvl,
          format: LevelFormat.DECIMAL,
          text: `%${lvl + 1}.`,
          alignment: AlignmentType.LEFT,
          style: {
            paragraph: {
              indent: {
                left: convertInchesToTwip(0.3 + lvl * 0.28),
                hanging: convertInchesToTwip(0.25),
              },
            },
          },
        })),
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: 15840 },
        margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(`wrote ${OUT} (${buf.length} bytes, ${children.length} blocks)`);
});
