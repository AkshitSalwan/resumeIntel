import AppKit
import PDFKit
import Foundation

let base = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let verify = base.appendingPathComponent("verification", isDirectory: true)
let renders = verify.appendingPathComponent("rendered", isDirectory: true)
let names = [
  "01_Project_Abstract.pdf", "02_Technical_Documentation.pdf",
  "03_Originality_and_Contribution_Report.pdf", "04_System_Architecture_and_Workflows.pdf",
  "05_Repository_and_Development_Evidence.pdf", "ResumeIntel_Supporting_Documents.pdf"
]
var results: [[String: Any]] = []
var extracted = ""
for name in names {
  let url = base.appendingPathComponent(name)
  guard let document = PDFDocument(url: url) else { fatalError("Cannot open \(name)") }
  var blank: [Int] = []
  var missingText: [Int] = []
  for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { fatalError("Missing page \(index + 1) in \(name)") }
    if (page.string ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { missingText.append(index + 1) }
    let bounds = page.bounds(for: .mediaBox)
    let scale = min(1400 / bounds.width, 1800 / bounds.height)
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(bounds.width * scale), pixelsHigh: Int(bounds.height * scale), bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let context = NSGraphicsContext(bitmapImageRep: rep)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    context.cgContext.setFillColor(NSColor.white.cgColor)
    context.cgContext.fill(CGRect(origin: .zero, size: rep.size))
    context.cgContext.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context.cgContext)
    NSGraphicsContext.restoreGraphicsState()
    if name == "04_System_Architecture_and_Workflows.pdf" || name == "ResumeIntel_Supporting_Documents.pdf" {
      let image = rep.representation(using: .png, properties: [:])!
      let out = renders.appendingPathComponent(name.replacingOccurrences(of: ".pdf", with: "") + String(format: "_page_%03d.png", index + 1))
      try image.write(to: out)
    }
    let pixels = rep.representation(using: .png, properties: [:])!
    if pixels.count < 8000 { blank.append(index + 1) }
  }
  let text = (0..<document.pageCount).compactMap { document.page(at: $0)?.string }.joined(separator: "\n")
  extracted += "\n\n===== \(name) =====\n\(text)\n"
  let encrypted = document.isEncrypted
  results.append(["file": name, "bytes": try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? -1, "pages": document.pageCount, "encrypted": encrypted, "blankPages": blank, "pagesWithoutExtractableText": missingText, "textCharacters": text.count])
}
let data = try JSONSerialization.data(withJSONObject: ["validatedAt": ISO8601DateFormatter().string(from: Date()), "documents": results], options: [.prettyPrinted, .sortedKeys])
try data.write(to: verify.appendingPathComponent("supporting_pdf_validation.json"))
try extracted.write(to: verify.appendingPathComponent("supporting_pdf_extracted_text.txt"), atomically: true, encoding: .utf8)
print(String(data: data, encoding: .utf8)!)
