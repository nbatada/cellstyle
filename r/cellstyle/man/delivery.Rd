\name{save_for_paper_and_slides}
\alias{save_for_paper_and_slides}
\title{Save a ggplot for manuscript and PowerPoint use}
\description{Writes an atomic manuscript PDF and proportionally fitted PowerPoint SVG delivery bundle.}
\usage{save_for_paper_and_slides(plot, directory, slide_box_mm = c(250, 145), min_slide_text_pt = 16)}
\arguments{\item{plot}{A native ggplot object.}\item{directory}{A new output directory whose parent exists.}\item{slide_box_mm}{Maximum slide placement width and height in millimetres.}\item{min_slide_text_pt}{Minimum requested SVG text size at placement in points.}}
\value{Invisibly, a receipt also saved as \code{receipt.json}.}
\details{The source size is \code{cellstyle_size_mm}, or the 90 by 60 mm fallback. The SVG root has explicit millimetre dimensions and an svglite viewBox so PowerPoint can preserve aspect ratio on import. PASS means serialized text meets a conservative placement floor; it is not a certification of PowerPoint rendering or scientific acceptance.}
