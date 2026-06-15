#import "styles.typ": *

#let card(body, fill: paper, stroke: border, inset: 8pt, radius: 7pt) = block(
  fill: fill,
  stroke: 0.55pt + stroke,
  radius: radius,
  inset: inset,
  above: 5pt,
  below: 6pt,
  breakable: false,
)[#body]

#let tip(body) = card(body, fill: tipbg)
#let mistake(body) = card(body, fill: mistakebg, stroke: rgb("#C56C6C"))
#let example(body) = card(body, fill: examplebg, stroke: rgb("#D6A85C"))
#let formula-card(name, math-body, meaning, condition, number: none) = card(fill: formulabg)[
  #strong(name) #if number != none { h(1fr); text(size: 8.5pt, fill: subtext)[(#number)] }
  #align(center)[#math.equation(block: true, math-body)]
  #text(size: 9.2pt)[含义：#meaning。适用：#condition。]
]

#let figure-block(no, title, path, caption) = block(above: 5pt, below: 8pt, breakable: false)[
  #align(center)[#image(path, width: 86%)]
  #align(center)[#text(size: 8.8pt, fill: subtext)[图 #no #title]]
  #align(center)[#text(size: 8.5pt, fill: subtext)[#caption]]
]

#let step-list(items) = {
  enum(numbering: "1.", ..items.map(x => [#x]))
}

#let cover(title, subtitle, meta) = {
  pagebreak(weak: true)
  v(42mm)
  text(size: 13pt, weight: "bold", fill: primary)[StudyPilot AI]
  v(6mm)
  text(size: 31pt, weight: "bold")[#title]
  v(5mm)
  text(size: 14pt, fill: subtext)[#subtitle]
  v(14mm)
  grid(columns: (1fr, 1fr), gutter: 7pt, ..meta.map(m => card[
    #text(size: 8.8pt, fill: subtext)[#m.at("label")]
    #linebreak()
    #strong(m.at("value"))
  ]))
  pagebreak()
}

#let compact-toc(items, scene, path, hotspots) = card[
  = 目录与使用建议
  #grid(columns: (1.05fr, 1fr), gutter: 12pt)[
    #enum(numbering: "1.", ..items)
  ][
    #tip[
      #strong[适合场景：] #scene
      #linebreak()
      #strong[阅读路径：] #path
      #linebreak()
      #strong[高频重点：] #hotspots
    ]
  ]
]
