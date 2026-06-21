#let brand = rgb("#1f4f59")
#let accent = rgb("#b6432f")
#let paper = rgb("#fbfaf7")
#let line = rgb("#d8d4ca")
#let ink = rgb("#202124")
#let soft = rgb("#eef4f2")

#let lecture-style(kind: "review", body) = {
  set document(author: "StudyPilot AI", title: "StudyPilot PDF 2.0")
  set page(
    paper: "a4",
    margin: (x: 1.35cm, y: 1.3cm),
    fill: paper,
    numbering: "1",
    footer: context [
      #set text(size: 8pt, fill: rgb("#666"))
      #align(center)[StudyPilot PDF 2.0 · Evidence-first lecture notes · #counter(page).display()]
    ],
  )
  set text(font: ("PingFang SC", "Noto Sans CJK SC", "Helvetica"), size: if kind == "sprint" { 9.2pt } else { 9pt }, fill: ink)
  set par(justify: true, leading: 0.56em)
  show heading: it => {
    set text(fill: brand)
    it
  }
  body
}

#let cover(title, subtitle) = {
  rect(width: 100%, fill: brand, inset: 18pt, radius: 4pt)[
    #set text(fill: white)
    #text(size: 21pt, weight: "bold")[#title]
    #v(6pt)
    #text(size: 10.5pt)[#subtitle]
    #v(8pt)
    #text(size: 8.5pt)[Evidence-first · Source-aligned · No free-form whole-PDF LLM]
  ]
  v(10pt)
}

#let callout(title, body) = block(
  width: 100%,
  fill: soft,
  stroke: (left: 3pt + brand),
  inset: 9pt,
  radius: 3pt,
)[
  #text(weight: "bold", fill: brand)[#title]
  #v(3pt)
  #body
]

#let section-heading(no, title) = {
  v(8pt)
  grid(columns: (24pt, 1fr), gutter: 8pt)[
    #circle(fill: brand, radius: 11pt)[#set text(fill: white, size: 8pt, weight: "bold"); #no]
  ][
    #text(size: 16pt, weight: "bold", fill: brand)[#title]
  ]
  v(5pt)
}

#let block-title(title) = {
  v(5pt)
  text(size: 10pt, weight: "bold", fill: accent)[#title]
  v(2pt)
}

#let priority(value) = block(fill: rgb("#fff2df"), stroke: 0.5pt + rgb("#e0b66f"), inset: 6pt, radius: 3pt)[
  #text(weight: "bold")[复习优先级]：#value
]

#let warning-box(body) = block(fill: rgb("#fff0f0"), stroke: 0.5pt + rgb("#d58181"), inset: 7pt, radius: 3pt)[
  #text(weight: "bold", fill: rgb("#9c2d2d"))[注意] #body
]

#let margin-note(kind, content) = block(width: 100%, fill: white, stroke: 0.45pt + line, inset: 6pt, radius: 3pt, below: 5pt)[
  #text(size: 7.4pt, weight: "bold", fill: if kind == "warning" { accent } else { brand })[#upper(kind)]
  #linebreak()
  #text(size: 7.4pt)[#content]
]

#let formula-card(title, formula-text, condition, source) = block(width: 100%, fill: white, stroke: 0.45pt + line, inset: 8pt, radius: 3pt, below: 5pt)[
  #text(weight: "bold")[#title]
  #v(3pt)
  #align(center)[#text(size: 11pt, weight: "bold")[#formula-text]]
  #v(2pt)
  #text(size: 7.7pt, fill: rgb("#555"))[条件：#condition]
  #linebreak()
  #text(size: 7.7pt, fill: rgb("#555"))[来源：#source]
]

#let exam-pattern(freq, score, types, refs) = block(fill: rgb("#f4f7fb"), stroke: 0.5pt + rgb("#9eb6d8"), inset: 7pt, radius: 3pt)[
  #text(weight: "bold", fill: brand)[真题考法]
  #v(3pt)
  #grid(columns: (1fr, 1fr), gutter: 6pt)[考频：近 5 年 #freq 次][均分/分值：#score]
  #grid(columns: (1fr,), gutter: 4pt)[题型：#types]
  #text(size: 7.8pt, fill: rgb("#555"))[真题：#refs]
]

#let example-card(source-type, source, body) = block(
  width: 100%,
  fill: white,
  stroke: 0.55pt + rgb("#c6bda9"),
  inset: 8pt,
  radius: 3pt,
  below: 8pt,
)[
  #grid(columns: (1fr, auto), gutter: 8pt)[
    #text(weight: "bold", fill: brand)[例题]
  ][
    #text(size: 7.5pt, fill: rgb("#666"))[#source-type]
  ]
  #text(size: 7.7pt, fill: rgb("#555"))[来源：#source]
  #v(4pt)
  #body
]

#let source-table(rows) = {
  block-title("来源对齐表")
  table(
    columns: (1.4fr, 2fr, 1.8fr, 2fr, 0.6fr),
    inset: 4pt,
    stroke: 0.35pt + line,
    fill: (_, y) => if y == 0 { brand } else if calc.even(y) { rgb("#f6f3ec") } else { white },
    text(fill: white, weight: "bold")[知识点],
    text(fill: white, weight: "bold")[教材],
    text(fill: white, weight: "bold")[PPT],
    text(fill: white, weight: "bold")[真题],
    text(fill: white, weight: "bold")[频次],
    ..rows.flatten(),
  )
  v(8pt)
}

#let question(no, kind, points, stem, options, source) = block(width: 100%, fill: white, stroke: 0.45pt + line, inset: 7pt, radius: 3pt, below: 5pt)[
  #text(weight: "bold")[#no. #kind（#points 分）]
  #linebreak()
  #stem
  #v(3pt)
  #for opt in options [#opt #linebreak()]
  #text(size: 7.5pt, fill: rgb("#666"))[来源：#source]
]

#let open-question(no, kind, points, stem, source) = block(width: 100%, fill: white, stroke: 0.45pt + line, inset: 7pt, radius: 3pt, below: 5pt)[
  #text(weight: "bold")[#no. #kind（#points 分）]
  #linebreak()
  #stem
  #v(3pt)
  #text(size: 7.5pt, fill: rgb("#666"))[来源：#source]
]
