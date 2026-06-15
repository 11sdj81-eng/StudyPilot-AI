#let bg = rgb("#F8F5EF")
#let paper = rgb("#FFFDF8")
#let primary = rgb("#6f936b")
#let border = rgb("#E6E0D6")
#let textc = rgb("#333333")
#let subtext = rgb("#6F6F6F")
#let tipbg = rgb("#EEF5EA")
#let formulabg = rgb("#F6F1E8")
#let examplebg = rgb("#FFF9EE")
#let mistakebg = rgb("#FFF1EF")

#set page(
  paper: "a4",
  margin: (x: 17mm, y: 16mm),
  fill: bg,
  header: align(center, text(size: 8.5pt, fill: subtext)[StudyPilot AI · 电磁场与电磁波]),
  footer: context align(center, text(size: 8.5pt, fill: subtext, counter(page).display("1"))),
)
#set text(font: ("Noto Sans CJK SC", "PingFang SC", "Arial"), size: 10.5pt, fill: textc, lang: "zh")
#set par(justify: true, leading: 0.63em)
#show heading.where(level: 1): it => block(above: 11pt, below: 7pt)[
  #text(size: 17pt, weight: "bold", fill: textc, it.body)
  #line(length: 100%, stroke: 0.8pt + primary)
]
#show heading.where(level: 2): it => block(above: 9pt, below: 5pt)[
  #text(size: 13.5pt, weight: "bold", fill: textc, it.body)
]
