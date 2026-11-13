0037
0038  export async function extractResumeText(type: SupportedResumeType, buffer: Buffer) {
0039    if (!hasValidFileSignature(type, buffer)) throw new Error('The file signature does not match its declared type.')
0040    if (type === 'application/pdf') {
0041      const { getDocument } = await import('pdfjs-dist/legacy/build/pdf.mjs')
0042      const document = await getDocument({
0043        data: new Uint8Array(buffer),
0044        isEvalSupported: false,
0045      }).promise
0046      try {
0047        const pages: string[] = []
0048        for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
0049          const page = await document.getPage(pageNumber)
0050          const content = await page.getTextContent()
0051          pages.push(content.items.map((item) => 'str' in item ? item.str : '').join(' '))
0052        }
0053        return assertReadableResumeText(pages.join('\n'))
0054      } finally {
0055        await document.cleanup()
0056        await document.destroy()
0057      }
0058    }
0059    const mammoth = await import('mammoth')
0060    return assertReadableResumeText((await mammoth.extractRawText({ buffer })).value)
0061  }
0062
0063  export function isSupportedResumeType(type: string): type is SupportedResumeType {
0064    return SUPPORTED_RESUME_TYPES.includes(type as SupportedResumeType)
0065  }
