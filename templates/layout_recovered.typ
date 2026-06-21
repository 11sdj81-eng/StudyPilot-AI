// Layout Recovered — TRUE_FINAL content, optimized readability

#let recovered(
  name: "", phone: "", email: "", github_url: "", direction: "",
  education: (:), projects: (), skills: (), honors: ()
) = {
  set page(paper: "a4", margin: (top: 0.25cm, bottom: 0.0cm, left: 1.3cm, right: 1.3cm))
  set text(font: ("Heiti SC", "PingFang SC"), size: 10pt, lang: "zh")
  set par(leading: 0.28em, first-line-indent: 0pt)

  let dark-blue = rgb(0, 51, 102)
  let sep = line(length: 100%, stroke: 0.4pt + rgb(180, 180, 180))
  let gray-sep = line(length: 100%, stroke: 0.3pt + rgb(210, 210, 210))

  // ═══ Header ═══
  grid(columns: (1fr, 2.3cm), column-gutter: 0.5cm,
    {
      text(size: 18pt, weight: "bold")[#name]
      v(0.02em)
      text(size: 10pt, fill: rgb(90, 90, 90))[#phone  |  #email]
      v(0.01em)
      text(size: 10pt, weight: "bold")[*GitHub：*#github_url]
      v(0.01em)
      text(size: 10pt)[*开源项目：*StudyPilot-AI、SmartVoiceSystem]
      v(0.01em)
      text(size: 10pt, fill: rgb(70, 70, 70))[*求职意向：*#direction]
    },
    {
      rect(width: 2.0cm, height: 2.8cm, stroke: 0.3pt + rgb(160, 160, 160), fill: rgb(250, 250, 250))[
        #set text(size: 7pt, fill: gray)
        #align(center + horizon)[证件照]
      ]
    },
  )

  v(0.06em)
  line(length: 100%, stroke: 0.5pt + black)

  // ═══ Education ═══
  v(0.02em)
  text(size: 11pt, weight: "bold", fill: dark-blue)[教育背景]
  v(0.01em)
  text(size: 10pt)[*#education.school*  |  #education.major  |  #education.degree]
  if "courses" in education {
    v(0.01em)
    text(size: 10pt)[主修课程：#education.courses]
  }

  // ═══ Projects ═══
  v(0.06em)
  sep
  v(0.02em)
  text(size: 11pt, weight: "bold", fill: dark-blue)[项目经历]

  // ── Project 1 ──
  v(0.04em)
  grid(columns: (1fr, auto), column-gutter: 0.3cm,
    { text(size: 10.5pt, weight: "bold")[#projects.at(0).name] },
    { text(size: 10pt, fill: rgb(100, 100, 100))[#projects.at(0).time] },
  )
  v(0.01em)
  text(size: 10pt)[*项目简介：*#projects.at(0).desc]
  v(0.01em)
  text(size: 10pt)[*技术栈：*#projects.at(0).tech]
  v(0.01em)
  text(size: 10pt)[*主要工作：*]
  v(0.01em)
  for bullet in projects.at(0).work {
    text(size: 10pt)[- #bullet]
    v(0.01em)
  }

  // ── Separator ──
  v(0.02em)
  gray-sep
  v(0.02em)

  // ── Project 2 ──
  grid(columns: (1fr, auto), column-gutter: 0.3cm,
    { text(size: 10.5pt, weight: "bold")[#projects.at(1).name] },
    { text(size: 10pt, fill: rgb(100, 100, 100))[#projects.at(1).time] },
  )
  v(0.01em)
  text(size: 10pt)[*项目简介：*#projects.at(1).desc]
  v(0.01em)
  text(size: 10pt)[*技术栈：*#projects.at(1).tech]
  v(0.01em)
  text(size: 10pt)[*主要工作：*]
  v(0.01em)
  for bullet in projects.at(1).work {
    text(size: 10pt)[- #bullet]
    v(0.01em)
  }

  // ═══ Skills ═══
  v(0.02em)
  sep
  v(0.02em)
  text(size: 11pt, weight: "bold", fill: dark-blue)[技术能力]
  v(0.03em)
  for skill in skills {
    text(size: 10pt)[*#skill.cat：*#skill.text]
    v(0.03em)
  }

  // ═══ Honors ═══
  v(0.02em)
  sep
  v(0.02em)
  text(size: 11pt, weight: "bold", fill: dark-blue)[荣誉与校园经历]
  v(0.03em)
  for h in honors {
    text(size: 10pt)[- #h]
    v(0.03em)
  }
}
