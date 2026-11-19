import AppKit
import Foundation
import PDFKit

let directory = URL(fileURLWithPath: CommandLine.arguments[1]).appendingPathComponent("verification")
let pdfURL = directory.appendingPathComponent("01_Source_Code_First_Last_10_Pages.pdf")
guard let document = PDFDocument(url: pdfURL) else { fatalError("Could not open PDF") }
let pages = [(1, "pdf_cover_preview.png"), (2, "pdf_first_source_page_preview.png"), (document.pageCount, "pdf_last_source_page_preview.png")]
for (number, name) in pages {
    guard let page = document.page(at: number - 1) else { fatalError("Missing page \(number)") }
    let image = page.thumbnail(of: NSSize(width: 800, height: 1132), for: .mediaBox)
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:]) else { fatalError("Could not render page \(number)") }
    try png.write(to: directory.appendingPathComponent(name))
}
print("PDFKit opened \(document.pageCount) pages and rendered cover, first source page, and last source page.")
